"""빈도 제한 — 토큰 버킷과 미들웨어.

`test_api.py` 는 한도를 끈 채로 돈다(`conftest.py`). 여기서는 자기 앱과 자기
한도를 세워 **제한이 실제로 걸리고 실제로 풀리는지**를 본다.

시간은 `check(key, now=...)` 로 직접 넣는다. `sleep` 으로 기다리면 테스트가
느려지고, 느린 기계에서 간헐적으로 깨진다.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.ratelimit import RateLimitMiddleware, TokenBucketLimiter


# --- 토큰 버킷 --------------------------------------------------------------


def test_한도까지는_통과하고_그_다음이_막힌다():
    limiter = TokenBucketLimiter(limit=3, window_sec=60)
    assert [limiter.check("ip", now=0) for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.check("ip", now=0) > 0


def test_거절할_때_언제_오면_되는지_알려준다():
    """거절만 하고 언제 풀리는지 말하지 않으면 클라이언트는 계속 두드린다."""
    limiter = TokenBucketLimiter(limit=60, window_sec=60)  # 초당 1개
    for _ in range(60):
        limiter.check("ip", now=0)

    retry_after = limiter.check("ip", now=0)
    assert retry_after == pytest.approx(1.0, abs=0.01)


def test_시간이_지나면_다시_통과한다():
    limiter = TokenBucketLimiter(limit=3, window_sec=60)  # 20초에 1개
    for _ in range(3):
        limiter.check("ip", now=0)
    assert limiter.check("ip", now=0) > 0

    assert limiter.check("ip", now=20) == 0.0  # 한 개 찼다
    assert limiter.check("ip", now=20) > 0     # 그 한 개를 방금 썼다


def test_버킷은_용량_넘게_쌓이지_않는다():
    """오래 쉬었다고 해서 그만큼 몰아 쓸 수 있으면 한도가 아니다."""
    limiter = TokenBucketLimiter(limit=3, window_sec=60)
    limiter.check("ip", now=0)
    assert [limiter.check("ip", now=100_000) for _ in range(3)] == [0.0, 0.0, 0.0]
    assert limiter.check("ip", now=100_000) > 0


def test_키가_다르면_서로의_한도를_먹지_않는다():
    limiter = TokenBucketLimiter(limit=2, window_sec=60)
    for _ in range(2):
        limiter.check("1.1.1.1", now=0)
    assert limiter.check("1.1.1.1", now=0) > 0
    assert limiter.check("2.2.2.2", now=0) == 0.0


def test_추적하는_키_수에_상한이_있다():
    """IP 를 바꿔 가며 들어오는 요청이 메모리를 무한히 키우면 안 된다."""
    limiter = TokenBucketLimiter(limit=5, window_sec=60, max_keys=10)
    for i in range(500):
        limiter.check(f"10.0.0.{i}", now=0)
    assert len(limiter._buckets) <= 10


def test_오래된_버킷은_청소된다():
    """가득 찬 버킷은 새 키와 구별할 수 없으므로 들고 있을 이유가 없다."""
    limiter = TokenBucketLimiter(limit=5, window_sec=60)
    for i in range(50):
        limiter.check(f"10.0.0.{i}", now=0)
    assert len(limiter._buckets) == 50

    limiter.check("새-손님", now=1000)  # 윈도가 지난 뒤 첫 요청이 청소를 부른다
    assert len(limiter._buckets) == 1


@pytest.mark.parametrize("bad", [(0, 60), (-1, 60), (60, 0), (60, -1)])
def test_말이_안_되는_설정은_거부한다(bad):
    limit, window = bad
    with pytest.raises(ValueError):
        TokenBucketLimiter(limit=limit, window_sec=window)


# --- 미들웨어 ---------------------------------------------------------------


def _app(limit: int = 2, window: float = 60, **kwargs) -> TestClient:
    app = FastAPI()

    @app.get("/api/assess")
    def assess() -> dict:
        return {"ok": True}

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    app.add_middleware(
        RateLimitMiddleware,
        limiter=TokenBucketLimiter(limit, window),
        **kwargs,
    )
    return TestClient(app)


def test_한도를_넘기면_429다():
    client = _app(limit=2)
    assert client.get("/api/assess").status_code == 200
    assert client.get("/api/assess").status_code == 200

    blocked = client.get("/api/assess")
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1
    assert "잦다" in blocked.json()["detail"]


def test_상태_점검은_한도에서_뺀다():
    """Render 의 주기적 상태 점검이 사용자 몫을 갉아먹으면 안 된다."""
    client = _app(limit=2)
    for _ in range(50):
        assert client.get("/api/health").status_code == 200
    assert client.get("/api/assess").status_code == 200


def test_XFF_는_기본적으로_믿지_않는다():
    """헤더를 믿으면 한 줄 적어 보내는 것만으로 한도를 우회한다."""
    client = _app(limit=1)
    assert client.get("/api/assess").status_code == 200
    blocked = client.get("/api/assess", headers={"X-Forwarded-For": "9.9.9.9"})
    assert blocked.status_code == 429


def test_프록시_뒤에서는_오른쪽_끝을_쓴다():
    """앞단이 진짜 주소를 **뒤에** 붙인다. 왼쪽은 클라이언트가 위조한 값이다."""
    client = _app(limit=1, trusted_hops=1)

    # 위조 부분만 다르고 프록시가 붙인 주소는 같다 -> 같은 사람으로 본다
    ok = client.get("/api/assess", headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.9"})
    blocked = client.get("/api/assess", headers={"X-Forwarded-For": "2.2.2.2, 203.0.113.9"})
    assert ok.status_code == 200
    assert blocked.status_code == 429

    # 프록시가 붙인 주소가 다르면 다른 사람이다
    other = client.get("/api/assess", headers={"X-Forwarded-For": "1.1.1.1, 198.51.100.4"})
    assert other.status_code == 200


def test_앱_기본값은_빈도_제한이_켜져_있다(monkeypatch):
    """`conftest.py` 가 테스트에서만 끄는 것이지 배포 기본값은 켜짐이다.

    기본값이 조용히 0 이 되면 이 파일의 나머지 테스트는 전부 통과하면서 정작
    배포된 API 에는 아무 제한이 없다. 그 상태를 여기서 잡는다.
    """
    import importlib

    import api.main

    monkeypatch.delenv("MAREUNGIL_RATE_LIMIT", raising=False)
    try:
        module = importlib.reload(api.main)
        assert module.RATE_LIMIT == 60
        assert module.RATE_WINDOW_SEC == 60
        assert module.TRUSTED_PROXY_HOPS == 0  # 프록시 뒤에서만 배포 설정으로 켠다
        assert any(m.cls is RateLimitMiddleware for m in module.app.user_middleware)
    finally:
        # `test_api.py` 는 자기 import 시점의 app 객체를 들고 있어 영향받지 않지만,
        # 모듈 상태는 원래대로(꺼짐) 돌려놓고 나간다.
        monkeypatch.setenv("MAREUNGIL_RATE_LIMIT", "0")
        importlib.reload(api.main)


# --- 실행 명령이 uvicorn 의 프록시 헤더 처리를 꺼두는가 ----------------------


@pytest.mark.parametrize("name", ["render.yaml", "make.ps1", "make.sh"])
def test_실행_명령이_프록시_헤더_처리를_끈다(root, name):
    """`--no-proxy-headers` 가 빠지면 빈도 제한이 헤더 한 줄로 우회된다.

    uvicorn 의 `--proxy-headers` 는 **기본으로 켜져 있고**, 소켓 상대가
    `--forwarded-allow-ips`(기본 `127.0.0.1`) 안에 들면 `X-Forwarded-For` 의
    **왼쪽 끝** — 클라이언트가 위조해 넣는 그 자리 — 로 `request.client` 를
    덮어쓴다. 그러면 `client_key()` 가 `trusted_hops=0` 으로 헤더를 안 믿어도
    이미 덮어써진 값을 소켓 주소인 줄 알고 쓴다.

    실측으로 확인한 차이다(한도 3, 소진 후 위조 XFF 4회):
        기본            -> [200, 200, 200, 200]  전부 통과, 우회됨
        --no-proxy-headers -> [429, 429, 429, 429]  막힘

    앞단을 믿을지는 `client_key()` 한 곳에서만 정한다. 이 플래그가 그 전제다.
    """
    text = (root / name).read_text(encoding="utf-8-sig")
    assert "uvicorn" in text, f"{name} 이 uvicorn 을 띄우지 않는다 — 테스트 전제가 낡았다"
    assert "--no-proxy-headers" in text, (
        f"{name} 에 --no-proxy-headers 가 없다. "
        f"X-Forwarded-For 한 줄로 빈도 제한이 우회된다"
    )
