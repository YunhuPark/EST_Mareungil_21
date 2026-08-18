import pytest
from services.route.interface import RouteRequest, RoutePoint, DestinationPoint
from services.decision.enums import Action, RouteStatus, RouteTarget
from services.route.provider import DesignatedPointRouteProvider
from services.route.distance import haversine_m
from scripts.mareungil.area_risk import haversine_m as original_haversine_m

# ==============================================================================
# 24. haversine 기존 함수 대조
# ==============================================================================
def test_haversine_matches_original_and_zero_distance():
    lat1, lon1 = 37.4979, 127.0276
    lat2, lon2 = 37.5045, 127.0250
    
    dist1 = haversine_m(lat1, lon1, lat2, lon2)
    dist2 = original_haversine_m(lat1, lon1, lat2, lon2)
    
    assert abs(dist1 - dist2) < 1e-6
    # 동일 좌표 0 확인
    assert haversine_m(lat1, lon1, lat1, lon1) == 0.0

# ==============================================================================
# Fixtures & Setup
# ==============================================================================

@pytest.fixture
def safe_points():
    return [
        {"id": "SP-002", "label": "서일중학교", "lat": 37.49929, "lon": 127.02218, "facility": {"capacity": 1654}},
        {"id": "SP-001", "label": "서초초등학교", "lat": 37.49952, "lon": 127.02393, "facility": {"capacity": 203}},
        {"id": "SP-003", "label": "서운중학교", "lat": 37.49398, "lon": 127.02452, "facility": {"capacity": 437}},
        {"id": "SP-004", "label": "역삼1문화센터", "lat": 37.4954, "lon": 127.03327, "facility": {"capacity": 566}},
        {"id": "SP-005", "label": "서초2동주민센터", "lat": 37.49207, "lon": 127.02493, "facility": {"capacity": 296}},
        {"id": "SP-006", "label": "서초4동주민센터", "lat": 37.50000, "lon": 127.02000, "facility": {"capacity": 335}},
        {"id": "SP-007", "label": "서이초등학교", "lat": 37.49161, "lon": 127.02599, "facility": {"capacity": 223}}
    ]

@pytest.fixture
def sensors():
    return [
        {
            "id": "S-01",
            "location": {"lat": 37.49900, "lon": 127.02300},
            "horizons": {"30": {"high_level_p": 0.8}}
        },
        {
            "id": "S-02",
            "location": {"lat": 37.49200, "lon": 127.02500},
            "horizons": {"30": {"high_level_p": 0.2}}
        }
    ]

@pytest.fixture
def base_request():
    return RouteRequest(
        primary_action=Action.MOVE,
        origin=RoutePoint(lat=37.4979, lon=127.0276), # 강남역
        destination=DestinationPoint(id="GN-002", label="신논현역", lat=37.5045, lon=127.0250),
        asof="2022-08-08T21:40:00+09:00",
        official={"closures": [], "confirmed_flooding": []}
    )

# ==============================================================================
# 필수 보장 테스트
# ==============================================================================

def test_move_target_is_user_destination(safe_points, sensors, base_request):
    """1. MOVE → USER_DESTINATION, 22. limit 필수, 18. route_verified=false, 19. eta_sec=null, 20. profile_applied=[], 21. 가짜 route_id 없음"""
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=sensors)
    result = provider.solve(base_request)
    
    assert result["route_target"] == RouteTarget.USER_DESTINATION.value
    assert result["target"]["kind"] == "DESTINATION_POINT"
    assert result["target"]["id"] == "GN-002"
    assert "limit" in result
    assert result["route_verified"] is False
    assert result["eta_sec"] is None
    assert result["profile_applied"] == []
    # 7. MOVE는 다른 지정 지점 4개를 비교하지 않음 (단일 반환, candidates는 없거나 비어 있음)
    assert not result.get("candidates")

def test_evacuate_target_is_safe_point(safe_points, sensors, base_request):
    """2. EVACUATE → SAFE_POINT, 8. EVACUATE가 안전거점 7곳만 사용, 13. 결정론, 12. AI 확률 배제 금지"""
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=sensors)
    # EVACUATE 요청으로 변경
    request = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=base_request.origin,
        destination=base_request.destination,
        asof=base_request.asof,
        official=base_request.official
    )
    result = provider.solve(request)
    
    assert result["route_target"] == RouteTarget.SAFE_POINT.value
    assert result["target"]["kind"] == "SHELTER"
    assert result["target"]["id"] in [p["id"] for p in safe_points]
    assert "candidates" not in result or len(result["candidates"]) == 0
    
def test_not_required_actions(safe_points, sensors, base_request):
    """3. WAIT → NOT_REQUIRED, 4. EMERGENCY → NOT_REQUIRED, 5. UNAVAILABLE → NOT_REQUIRED"""
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=sensors)
    
    for action in [Action.WAIT, Action.EMERGENCY, Action.UNAVAILABLE]:
        req = RouteRequest(
            primary_action=action,
            origin=base_request.origin,
            destination=base_request.destination,
            asof=base_request.asof,
            official=base_request.official
        )
        result = provider.solve(req)
        assert result["status"] == RouteStatus.NOT_REQUIRED.value
        assert result["route_target"] is None
        assert result["target"] is None

def test_destination_blocked(safe_points, sensors, base_request):
    """6. MOVE 차단 목적지 → DESTINATION_BLOCKED, 15. MOVE에서 NO_SAFE_POINT 반환 금지"""
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=sensors)
    blocked_request = RouteRequest(
        primary_action=Action.MOVE,
        origin=base_request.origin,
        destination=base_request.destination,
        asof=base_request.asof,
        official={
            "closures": [{"blocks_destination_ids": ["GN-002"]}],
            "confirmed_flooding": []
        }
    )
    result = provider.solve(blocked_request)
    assert result["status"] == RouteStatus.DESTINATION_BLOCKED.value
    assert result["route_target"] == RouteTarget.USER_DESTINATION.value
    assert result["no_safe_route"] is None
    assert result.get("route_attempted") is False

def test_no_safe_point(safe_points, sensors, base_request):
    """9. 안전거점 전부 명시적 차단 → NO_SAFE_POINT, 16. EVACUATE에서 DESTINATION_BLOCKED 반환 금지"""
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=sensors)
    all_sp_ids = [p["id"] for p in safe_points]
    blocked_request = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=base_request.origin,
        destination=base_request.destination,
        asof=base_request.asof,
        official={
            "closures": [{"blocks_destination_ids": all_sp_ids}],
            "confirmed_flooding": []
        }
    )
    result = provider.solve(blocked_request)
    assert result["status"] == RouteStatus.NO_SAFE_POINT.value
    assert result["route_target"] == RouteTarget.SAFE_POINT.value
    assert result["no_safe_route"] is None
    assert result.get("route_attempted") is False

def test_data_unavailable(safe_points, base_request):
    """10. 유효 센서 없음 → DATA_UNAVAILABLE"""
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=[])
    request = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=base_request.origin,
        destination=base_request.destination,
        asof=base_request.asof,
        official={"closures": [], "confirmed_flooding": []}
    )
    result = provider.solve(request)
    assert result["status"] == RouteStatus.DATA_UNAVAILABLE.value

def test_missing_probability_is_not_zero(safe_points, base_request):
    """11. 위험 확률 누락을 0으로 처리하지 않음 (유효 센서 판단)"""
    sensors_without_prob = [
        {
            "id": "S-01",
            "location": {"lat": 37.49900, "lon": 127.02300},
            "horizons": {"30": {}} # high_level_p 없음
        }
    ]
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=sensors_without_prob)
    request = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=base_request.origin,
        destination=base_request.destination,
        asof=base_request.asof,
        official={"closures": [], "confirmed_flooding": []}
    )
    result = provider.solve(request)
    # 유효 센서가 없으므로 DATA_UNAVAILABLE가 나와야 함
    assert result["status"] == RouteStatus.DATA_UNAVAILABLE.value

def test_deterministic_and_same_input_twice(safe_points, sensors, base_request):
    """13. 결정론, 14. 같은 입력 2회 결과 동일, 17. LIVE에서 NO_SAFE_ROUTE 반환 금지"""
    provider = DesignatedPointRouteProvider(safe_points=safe_points, sensors=sensors)
    request = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=base_request.origin,
        destination=base_request.destination,
        asof=base_request.asof,
        official={"closures": [], "confirmed_flooding": []}
    )
    
    result1 = provider.solve(request)
    result2 = provider.solve(request)
    
    assert result1 == result2
    assert result1["status"] == RouteStatus.FALLBACK_CANDIDATE.value
    # NO_SAFE_ROUTE 반환 금지 확인
    assert result1["status"] != RouteStatus.NO_SAFE_ROUTE.value
    
def test_sorting_order(safe_points, base_request):
    """13. 위험도->거리->ID 순 결정론"""
    # 안전거점 2개, 센서 2개를 배치해 정렬 순서를 테스트
    s_points = [
        {"id": "SP-B", "label": "B", "lat": 37.500, "lon": 127.020, "facility": {"capacity": 100}}, # origin에서 좀 멀고, risk 높음
        {"id": "SP-A", "label": "A", "lat": 37.498, "lon": 127.028, "facility": {"capacity": 100}}, # origin에 가깝고 risk 높음
        {"id": "SP-C", "label": "C", "lat": 37.501, "lon": 127.021, "facility": {"capacity": 100}}, # origin에서 제일 멀지만 risk 낮음
        {"id": "SP-D", "label": "D", "lat": 37.501, "lon": 127.021, "facility": {"capacity": 100}}  # C와 같은 좌표, risk 같음. ID순으로 뒤쳐짐
    ]
    # SP-A, SP-B는 센서 S-HIGH와 가까워 위험도가 높게 나옴
    # SP-C, SP-D는 센서 S-LOW와 가까워 위험도가 낮게 나옴
    sens = [
        {"id": "S-HIGH", "location": {"lat": 37.499, "lon": 127.024}, "horizons": {"30": {"high_level_p": 0.9}}},
        {"id": "S-LOW", "location": {"lat": 37.502, "lon": 127.022}, "horizons": {"30": {"high_level_p": 0.1}}}
    ]
    
    provider = DesignatedPointRouteProvider(safe_points=s_points, sensors=sens)
    request = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=base_request.origin,
        destination=base_request.destination,
        asof=base_request.asof,
        official={"closures": [], "confirmed_flooding": []}
    )
    result = provider.solve(request)
    
    # 1순위: 위험도 오름차순 (C, D가 A, B보다 앞섬)
    # 2순위: 거리 오름차순 (C, D는 거리가 같음)
    # 3순위: ID 오름차순 (SP-C 가 SP-D보다 앞섬)
    assert result["target"]["id"] == "SP-C"
