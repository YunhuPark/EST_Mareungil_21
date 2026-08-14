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


def test_응답이_픽스처_출처임을_밝힌다(client):
    """mock 을 실제 모델 결과처럼 표현하지 않는다."""
    body = client.get("/api/assess").json()
    assert body["source_kind"] == "FIXTURE"


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


def test_목적지를_바꾸면_거리를_지어내지_않는다(client):
    """경로 엔진이 없으므로 다시 계산할 수 없다. 없는 값을 채우지 않는다."""
    body = client.get("/api/assess", params={"destination": "GN-002"}).json()
    assert body["route"]["distance_m"] is None
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
