"""통합 API 테스트 — 수직 슬라이스가 실제로 도는지 본다.

픽스처 → API → AssessResponse 까지가 이 테스트의 범위다.
UI 렌더링은 `web/src/App.test.tsx` 가 본다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


def test_헬스체크(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "DS-S1" in body["scenarios"]


def test_기본_시나리오가_계약을_통과한다(client):
    """API 가 응답 직전에 스스로 계약을 검증하므로 200 이면 통과했다는 뜻이다."""
    res = client.get("/api/assess")
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["decision"]["action"] == "MOVE"
    assert body["route"]["route_target"] == "USER_DESTINATION"
    assert body["route"]["route_attempted"] is True


def test_응답이_출처를_시나리오별로_밝힌다(client):
    """P0-6. 실제 경로 엔진으로 재현되는 시나리오는 LIVE_PIPELINE, 시설 만석처럼
    재현 불가능한 시나리오는 FIXTURE로 남는다 - mock 을 실제 결과처럼 표현하지
    않는다는 원칙은 그대로다.
    """
    live = client.get("/api/assess", params={"scenario": "DS-S1"}).json()
    assert live["source_kind"] == "LIVE_PIPELINE"

    stub = client.get("/api/assess", params={"scenario": "DS-S7"}).json()
    assert stub["source_kind"] == "FIXTURE"


def test_고립_신고가_EMERGENCY로_간다(client):
    """M-19. 고립 신고는 `decide()` 규칙 1 이며 다른 모든 신호보다 먼저 이긴다.

    `DS-S1` 은 평소 `MOVE` 다. 신고 하나로 `EMERGENCY` 가 되고 경로는
    `NOT_REQUIRED` 가 된다 — 자력 이동이 어려운 상태에 경로를 안내하지 않는다.
    """
    before = client.get("/api/assess", params={"scenario": "DS-S1"}).json()
    assert before["decision"]["action"] == "MOVE"
    assert before["decision"]["user_state"]["trapped"] is False

    res = client.get("/api/assess", params={"scenario": "DS-S1", "trapped": "true"})
    assert res.status_code == 200, res.text
    after = res.json()

    assert after["decision"]["user_state"]["trapped"] is True
    assert after["decision"]["action"] == "EMERGENCY"
    assert after["route"]["status"] == "NOT_REQUIRED"
    # 판정이 바뀐 것이지 출처가 바뀐 것이 아니다.
    assert after["source_kind"] == before["source_kind"]


def test_고립_신고는_끄는_방향으로_동작하지_않는다(client):
    """`trapped=false` 가 픽스처의 고립 상태를 뒤집으면 안 된다.

    기본값이 `False` 라서, 끄는 방향까지 적용하면 `DS-S4` 를 그냥 불렀을 때
    `EMERGENCY` 가 조용히 풀린다. 그건 사용자가 취소한 것이 아니라 기본값이
    덮어쓴 것이다. **신고는 사용자만 만들고 아무도 대신 지우지 않는다.**
    """
    for params in ({"scenario": "DS-S4"}, {"scenario": "DS-S4", "trapped": "false"}):
        body = client.get("/api/assess", params=params).json()
        assert body["decision"]["user_state"]["trapped"] is True, params
        assert body["decision"]["action"] == "EMERGENCY", params


def test_UI가_항상_표시할_값이_들어있다(client):
    """설계서 12장. 위험·위치·행동·시각·119 문구·면책."""
    body = client.get("/api/assess").json()
    assert body["decision"]["service_risk_level"]
    assert body["location"]["label"]
    assert body["decision"]["action"]
    assert body["clock"]["label"]
    assert body["clock"]["mode"] == "REPLAY"
    assert body["notice"]["disclaimer"].strip()
    assert body["notice"]["route_limit"].strip()


def test_이유는_최대_3개다(client):
    """F-03. 계약이 maxItems 3 으로 막는다."""
    body = client.get("/api/assess").json()
    assert 1 <= len(body["decision"]["reasons"]) <= 3
    for reason in body["decision"]["reasons"]:
        assert reason["basis"] in {"OFFICIAL_GUIDANCE", "AI_PREDICTION", "TEAM_RULE"}


def test_경로는_검증되지_않은_후보다(client):
    """RT-02. 기본은 FALLBACK_CANDIDATE 이고 route_verified 는 false 다."""
    route = client.get("/api/assess").json()["route"]
    assert route["route_verified"] is False
    assert route["status"] == "FALLBACK_CANDIDATE"
    assert route["limit"]


def test_목적지는_필수이며_null이_아니다(client):
    """F-19 / R13."""
    dest = client.get("/api/assess").json()["decision"]["user_state"]["destination"]
    assert dest is not None
    assert dest["id"] and dest["label"]


def test_목적지_선택이_응답에_반영된다(client):
    """UI-10. 목록에서 고른 지점이 도달 대상이 된다."""
    body = client.get("/api/assess", params={"destination": "GN-002"}).json()
    assert body["decision"]["user_state"]["destination"]["id"] == "GN-002"
    assert body["route"]["target"]["id"] == "GN-002"


def test_목적지를_바꾸면_실거리가_계산된다(client):
    """P0-6. DS-S1(LIVE)은 실제 경로 엔진이 haversine 로 실거리를 낸다.

    eta_sec 은 소요시간 추정 로직이 아직 없어 여전히 None 이다 - 없는 값을
    지어내지 않는다는 원칙은 eta_sec 에는 그대로 적용된다.
    """
    body = client.get("/api/assess", params={"destination": "GN-002"}).json()
    assert isinstance(body["route"]["distance_m"], (int, float))
    assert body["route"]["distance_m"] > 0
    assert body["route"]["eta_sec"] is None


def test_목적지를_바꿔도_위험과_행동은_그대로다(client):
    """설계서 5.3. 목적지는 경로 입력이지 위험 판정 입력이 아니다."""
    base = client.get("/api/assess").json()
    moved = client.get("/api/assess", params={"destination": "GN-002"}).json()
    assert moved["decision"]["action"] == base["decision"]["action"]
    assert moved["decision"]["service_risk_level"] == base["decision"]["service_risk_level"]


def test_목록_밖_목적지는_거부한다(client):
    """RT-14 / RT-15. 자유 좌표·자유 텍스트 입력을 받지 않는다."""
    assert client.get("/api/assess", params={"destination": "없는지점"}).status_code == 400


def test_없는_시나리오는_404다(client):
    assert client.get("/api/assess", params={"scenario": "DS-S99"}).status_code == 404


def test_지정_지점_목록을_제공한다(client):
    body = client.get("/api/destinations").json()
    assert len(body["points"]) >= 1
    assert body["scope"]["radius_m"] > 0
    assert "안전" in body["note"]  # 목록 등재가 안전 보장이 아니라는 안내


def test_같은_요청은_같은_응답을_준다(client):
    """N-04 재현성."""
    first = client.get("/api/assess").json()
    second = client.get("/api/assess").json()
    assert first == second


# --- 프로필 (M-37) ----------------------------------------------------------


def test_프로필_선택이_응답에_반영된다(client):
    body = client.get("/api/assess", params={"profile": ["ELDERLY", "WITH_CHILD"]}).json()
    assert body["decision"]["user_state"]["profiles"] == ["ELDERLY", "WITH_CHILD"]


def test_프로필은_경로_후보_순서에_적용된다(client):
    """M-37. 고른 프로필은 우회 상한 1.15를 통해 후보 순서에 반영된다.

    경로 엔진이 `request.profiles`를 받아 우회 상한 이내에서 위험도 우선으로
    정렬하며, 적용된 프로필은 `route.profile_applied`에 담겨 반환된다.
    """
    body = client.get("/api/assess", params={"profile": ["ELDERLY"]}).json()
    assert body["decision"]["user_state"]["profiles"] == ["ELDERLY"]
    assert body["route"].get("profile_applied") == ["ELDERLY"]


def test_프로필은_위험과_행동을_바꾸지_않는다(client):
    """M-37. 사용자 유형으로 안전 기준을 완화하지도, 강화하지도 않는다."""
    base = client.get("/api/assess").json()
    with_profile = client.get("/api/assess", params={"profile": ["ELDERLY"]}).json()
    assert with_profile["decision"]["action"] == base["decision"]["action"]
    assert (
        with_profile["decision"]["service_risk_level"]
        == base["decision"]["service_risk_level"]
    )


def test_MVP_밖_프로필은_거부한다(client):
    """X1 / C-14. WHEELCHAIR·WITH_PET 은 검증 데이터 부족으로 계약 enum 밖이다.

    400 이어야 한다. 그냥 통과시키면 계약 검증에서 500 이 나는데, 그건 사용자
    입력 오류를 서버 오류로 보고하는 것이다.
    """
    assert client.get("/api/assess", params={"profile": ["WHEELCHAIR"]}).status_code == 400


# --- 화면이 자기 모순을 말하지 않는가 ----------------------------------------


@pytest.mark.parametrize("scenario", ["DS-S1", "DS-S4", "DS-S6", "DS-S7", "DS-S8"])
def test_대표_사유는_항상_이유_목록_안에_있다(client, scenario):
    """**이 파일에서 가장 중요한 불변식.**

    화면은 `decision.reasons` 만 렌더한다(`App.tsx` -> `ReasonList`). `reason_code`
    는 계약 필드일 뿐 어디에도 찍히지 않는다. 그래서 대표 사유가 목록에 없으면
    **사용자에게 도달하지 않는다.**

    깨진 적이 있다: `DS-S6` 의 `reason_code` 는 `ROUTE_DESTINATION_BLOCKED` 인데
    이유 목록은 `[NO_TRIGGER]` 뿐이라, 경로 카드가 "목적지 차단"을 띄우는 동안
    이유 카드는 "행동을 바꿀 조건이 확인되지 않았습니다"를 보여줬다.
    """
    decision = client.get("/api/assess", params={"scenario": scenario}).json()["decision"]
    codes = [r["code"] for r in decision["reasons"]]

    assert decision["reason_code"] in codes, (
        f"{scenario}: 대표 사유 {decision['reason_code']} 가 이유 목록 {codes} 에 없다 — "
        f"화면에서 사라지는 문구다."
    )


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [("DS-S6", "ROUTE_DESTINATION_BLOCKED"), ("DS-S8", "ROUTE_NO_SAFE_POINT")],
)
def test_경로_실패_사유가_화면_이유에_남는다(client, scenario, expected):
    """M-15·M-16 유지 조합. 행동은 그대로지만 **실패 사유는 말해야 한다.**

    `route_postprocess_applied` 가 false 라 전환 배너도 뜨지 않는다. 이 사유가
    목록에서 빠지면 화면 어디에도 "왜 안내가 멈췄는지"가 남지 않는다.
    """
    body = client.get("/api/assess", params={"scenario": scenario}).json()
    codes = [r["code"] for r in body["decision"]["reasons"]]

    assert expected in codes, f"{scenario}: {expected} 가 이유 목록 {codes} 에서 빠졌다"
    assert body["decision"]["reason_code"] == expected


def test_이유_목록은_경로_사유를_붙여도_상한을_지킨다(client):
    """C-15. 계약 `maxItems: 3` 은 사유를 덧붙인 뒤에도 유효하다."""
    for scenario in ("DS-S1", "DS-S4", "DS-S6", "DS-S7", "DS-S8"):
        reasons = client.get("/api/assess", params={"scenario": scenario}).json()["decision"]["reasons"]
        assert 1 <= len(reasons) <= 3, scenario
