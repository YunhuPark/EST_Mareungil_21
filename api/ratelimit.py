"""요청 빈도 제한 — 무의존 인메모리 토큰 버킷.

왜 라이브러리를 쓰지 않는가
---------------------------
`slowapi`·`redis` 를 붙이면 배포에 부품이 하나 는다. 이 저장소는 "쓰지 않는
라이브러리는 미리 넣지 않는다"(`requirements-dev.txt`)를 규칙으로 두고 있고,
막으려는 것도 분산 공격이 아니라 **무료 티어 한 대를 혼자 갈아 넣는 요청** 하나다.
그 정도는 표준 라이브러리로 충분하다.

무엇을 막고 무엇을 못 막는가
----------------------------
- 막는다: 한 IP 가 초당 수십 번씩 두드려 인스턴스를 마비시키는 것.
- 못 막는다: IP 를 바꿔 가며 들어오는 분산 공격. 그건 앞단(CDN·WAF)의 일이다.

**상태는 프로세스 안에만 있다.** 워커를 여럿 띄우면 워커마다 따로 세고
(`render.yaml` 은 단일 워커다), 재시작하면 초기화된다. 둘 다 이 목적에는 문제가
되지 않는다 — 정확한 회계가 아니라 폭주 차단이 목적이다.

왜 고정 윈도가 아니라 토큰 버킷인가
-----------------------------------
고정 윈도는 경계에서 두 배가 통과한다(59초에 60번, 61초에 또 60번). 토큰 버킷은
키마다 float 두 개만 들고도 그 구멍이 없고, 잠깐의 버스트는 허용하면서 평균
속도를 지킨다. 화면이 한 번 움직일 때 API 를 세 번 부르는 이 앱에 맞는 모양이다.
"""

from __future__ import annotations

import math
import time
from collections import OrderedDict

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class TokenBucketLimiter:
    """키(보통 IP)마다 토큰 버킷 하나.

    `limit` 개를 담는 버킷이 `window_sec` 동안 가득 차도록 새어 들어온다. 요청
    하나가 토큰 하나를 쓴다. 비어 있으면 거절하고 **몇 초 뒤에 오면 되는지**를
    돌려준다 — 거절만 하고 언제 풀리는지 말하지 않으면 클라이언트는 계속 두드린다.

    Args:
        limit: 버킷 용량. 순간 최대 몇 번까지 몰아 쓸 수 있는지이기도 하다.
        window_sec: 빈 버킷이 다시 가득 차는 데 걸리는 시간.
        max_keys: 추적할 키의 상한. **메모리를 묶어두기 위한 값이다** — 이것이
            없으면 IP 를 바꿔 가며 들어오는 요청이 딕셔너리를 무한히 키운다.
            넘치면 가장 오래 안 쓰인 키부터 버린다.
    """

    def __init__(self, limit: int, window_sec: float, max_keys: int = 10_000) -> None:
        if limit <= 0 or window_sec <= 0:
            raise ValueError("limit 과 window_sec 은 양수여야 한다")
        self.limit = limit
        self.window_sec = float(window_sec)
        self.max_keys = max_keys
        self._rate = limit / float(window_sec)  # 초당 채워지는 토큰
        #: key -> (남은 토큰, 마지막으로 계산한 시각). LRU 순서를 쓰므로 OrderedDict.
        self._buckets: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self._last_purge = 0.0

    def check(self, key: str, now: float | None = None) -> float:
        """토큰 하나를 쓴다.

        Returns:
            `0.0` 이면 통과. 양수면 거절이며 **그 초만큼 뒤에 다시 오라**는 뜻이다.

        `now` 는 테스트가 시간을 직접 넘기기 위한 자리다. 실제로는 `monotonic()`
        을 쓴다 — 시스템 시계가 뒤로 조정돼도 버킷이 뒤틀리지 않아야 한다.
        """
        now = time.monotonic() if now is None else now
        self._purge(now)

        entry = self._buckets.get(key)
        if entry is None:
            if len(self._buckets) >= self.max_keys:
                self._buckets.popitem(last=False)  # 가장 오래 안 쓰인 것부터 버린다
            tokens = float(self.limit)
        else:
            tokens, last = entry
            # 흐른 시간만큼 채운다. 용량을 넘겨 쌓이지는 않는다.
            tokens = min(float(self.limit), tokens + (now - last) * self._rate)

        if tokens >= 1.0:
            self._buckets[key] = (tokens - 1.0, now)
            self._buckets.move_to_end(key)
            return 0.0

        self._buckets[key] = (tokens, now)
        self._buckets.move_to_end(key)
        return (1.0 - tokens) / self._rate

    def _purge(self, now: float) -> None:
        """가득 찬 버킷은 새 키와 구별할 수 없으므로 지운다.

        매 요청마다 전체를 훑으면 그 자체가 부하다. 윈도 하나에 한 번만 쓴다.
        """
        if now - self._last_purge < self.window_sec:
            return
        self._last_purge = now
        cutoff = now - self.window_sec
        stale = [key for key, (_, last) in self._buckets.items() if last <= cutoff]
        for key in stale:
            del self._buckets[key]


def client_key(request: Request, trusted_hops: int = 0) -> str:
    """이 요청을 누구 앞으로 달아둘 것인가.

    `trusted_hops` 가 0 이면 **소켓 상대 주소만 믿는다.** 프록시 뒤가 아니라면
    이것이 맞고, `X-Forwarded-For` 는 클라이언트가 마음대로 적어 보낼 수 있으므로
    믿으면 한도를 그냥 우회당한다.

    프록시 뒤(Render 등)라면 앞단이 **자기가 받은 상대의 주소를 뒤에 덧붙인다.**
    그래서 클라이언트가 위조해 보낸 값들은 왼쪽에 쌓이고, 신뢰할 수 있는 값은
    오른쪽 끝에 있다. 신뢰하는 프록시가 n 단이면 오른쪽에서 n 번째를 쓴다.

        X-Forwarded-For: 1.2.3.4(위조), 203.0.113.9(프록시가 붙인 진짜)
        trusted_hops=1 -> 203.0.113.9

    자리 수가 모자라면 위조 가능성이 있으므로 소켓 주소로 되돌아간다.

    .. warning::
       **uvicorn 을 `--no-proxy-headers` 로 띄워야 이 함수가 의미를 갖는다.**

       uvicorn 의 `--proxy-headers` 는 **기본으로 켜져 있고**, 소켓 상대가
       `--forwarded-allow-ips`(기본 `127.0.0.1`) 안에 들면 `X-Forwarded-For` 의
       **왼쪽 끝** 값으로 `request.client` 를 통째로 덮어쓴다. 하필 왼쪽 끝은
       클라이언트가 위조해 넣는 자리다. 그대로 두면 여기서 `trusted_hops=0` 을
       주고 헤더를 안 믿는다고 해도, 이미 덮어써진 값을 소켓 주소인 줄 알고 쓰게
       된다 — 헤더 한 줄로 한도를 우회당한다(실측 확인).

       그래서 앞단 신뢰 여부는 **이 함수 한 곳에서만** 정한다. uvicorn 쪽은 끄고,
       `render.yaml`·`make.ps1`·`make.sh` 가 그 플래그를 들고 있다.
    """
    if trusted_hops > 0:
        chain = [
            part.strip()
            for part in request.headers.get("x-forwarded-for", "").split(",")
            if part.strip()
        ]
        if len(chain) >= trusted_hops:
            return chain[-trusted_hops]
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """한도를 넘긴 요청을 429 로 돌려보낸다.

    `exempt_paths` 는 한도에서 빼는 경로다. 기본으로 `/api/health` 를 뺀다 —
    Render 의 상태 점검이 주기적으로 같은 주소에서 들어오는데, 그것이 한도를
    갉아먹으면 정작 사용자가 막힌다.
    """

    def __init__(
        self,
        app,
        limiter: TokenBucketLimiter,
        trusted_hops: int = 0,
        exempt_paths: frozenset[str] = frozenset({"/api/health"}),
    ) -> None:
        super().__init__(app)
        self.limiter = limiter
        self.trusted_hops = trusted_hops
        self.exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next):
        if request.url.path in self.exempt_paths:
            return await call_next(request)

        retry_after = self.limiter.check(client_key(request, self.trusted_hops))
        if retry_after > 0:
            return JSONResponse(
                {"detail": "요청이 너무 잦다. 잠시 뒤 다시 시도하라."},
                status_code=429,
                headers={"Retry-After": str(max(1, math.ceil(retry_after)))},
            )
        return await call_next(request)
