import json
import os
import pytest
import jsonschema
from services.route.provider import DesignatedPointRouteProvider
from services.route.interface import RouteRequest, RoutePoint, DestinationPoint
from services.decision.enums import Action, RouteStatus, RouteTarget

def load_json(filepath):
    path = os.path.join(os.path.dirname(__file__), "..", filepath)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def safe_route_schema():
    # Load all relevant schemas to resolve refs if needed
    # Actually, jsonschema can handle it if we load the schema. Wait, $ref might need a resolver.
    # safe_route.schema.json only uses internal $defs, so it's self-contained!
    return load_json("contracts/schema/safe_route.schema.json")

@pytest.fixture
def real_safe_points():
    data = load_json("contracts/safe_points.json")
    return data["points"]

@pytest.fixture
def real_destinations():
    return load_json("contracts/destinations.json")

@pytest.fixture
def real_sensors():
    # S3 peak has active sensors
    risk_data = load_json("contracts/fixtures/risk_S3_peak.json")
    return risk_data.get("sensors", [])

@pytest.fixture
def official_0808():
    return load_json("contracts/fixtures/official/official_0808.json")

def test_evacuate_real_data(real_safe_points, real_sensors, official_0808, safe_route_schema):
    provider = DesignatedPointRouteProvider(safe_points=real_safe_points, sensors=real_sensors)
    origin = RoutePoint(lat=37.4979, lon=127.0276) # 강남역
    dest = DestinationPoint(id="GN-002", label="신논현역", lat=37.5045, lon=127.0250)
    
    req = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=origin,
        destination=dest,
        asof="2022-08-08T21:40:00+09:00",
        official=official_0808
    )
    
    # 두 번 실행
    res1 = provider.solve(req)
    res2 = provider.solve(req)
    assert res1 == res2
    
    print("\n[EVACUATE Target ID]", res1["target"]["id"] if res1.get("target") else None)
    
    # 1. 실제 안전거점이 7곳인가
    assert len(real_safe_points) == 7
    # 2. 유효 센서가 1곳 이상인가
    valid_sensors = [s for s in real_sensors if "location" in s and "lat" in s["location"] and "horizons" in s and "30" in s["horizons"] and "high_level_p" in s["horizons"]["30"]]
    assert len(valid_sensors) > 0
    # 3. FALLBACK_CANDIDATE 반환
    assert res1["status"] == RouteStatus.FALLBACK_CANDIDATE.value
    # 4. route_target=SAFE_POINT
    assert res1["route_target"] == RouteTarget.SAFE_POINT.value
    # 5. target ID가 7곳 중 하나
    sp_ids = [p["id"] for p in real_safe_points]
    assert res1["target"]["id"] in sp_ids
    # 6. target.kind=SHELTER
    assert res1["target"]["kind"] == "SHELTER"
    # 7. route_verified=false, route_attempted=true, no_safe_route=false, eta_sec=null, profile_applied=[]
    assert res1["route_verified"] is False
    assert res1["route_attempted"] is True
    assert res1["no_safe_route"] is False
    assert res1["eta_sec"] is None
    assert res1["profile_applied"] == []
    # 8. candidates 없음
    assert "candidates" not in res1
    # 9. 한계 문구 존재
    assert "limit" in res1
    
    # 스키마 검증
    jsonschema.validate(instance=res1, schema=safe_route_schema)

def test_move_real_data(real_safe_points, real_sensors, real_destinations, official_0808, safe_route_schema):
    provider = DesignatedPointRouteProvider(safe_points=real_safe_points, sensors=real_sensors)
    origin = RoutePoint(lat=37.4979, lon=127.0276) # 강남역
    
    # destinations.json 에서 1개 선택 (GN-002)
    point = next(p for p in real_destinations["points"] if p["id"] == "GN-002")
    dest = DestinationPoint(id=point["id"], label=point["label"], lat=point["lat"], lon=point["lon"])
    
    req = RouteRequest(
        primary_action=Action.MOVE,
        origin=origin,
        destination=dest,
        asof="2022-08-08T21:40:00+09:00",
        official=official_0808
    )
    
    res1 = provider.solve(req)
    res2 = provider.solve(req)
    assert res1 == res2
    
    print("\n[MOVE Distance]", res1.get("distance_m"))
    
    assert res1["status"] == RouteStatus.FALLBACK_CANDIDATE.value
    assert res1["route_target"] == RouteTarget.USER_DESTINATION.value
    assert res1["target"]["kind"] == "DESTINATION_POINT"
    assert res1["target"]["id"] == dest.id
    assert res1["route_verified"] is False
    assert res1["eta_sec"] is None
    assert "candidates" not in res1
    assert "limit" in res1
    
    jsonschema.validate(instance=res1, schema=safe_route_schema)

def test_data_unavailable_음성테스트(real_safe_points, official_0808, safe_route_schema):
    # 빈 센서
    provider = DesignatedPointRouteProvider(safe_points=real_safe_points, sensors=[])
    origin = RoutePoint(lat=37.4979, lon=127.0276)
    dest = DestinationPoint(id="GN-002", label="신논현역", lat=37.5045, lon=127.0250)
    
    req = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=origin,
        destination=dest,
        asof="2022-08-08T21:40:00+09:00",
        official=official_0808
    )
    
    res = provider.solve(req)
    assert res["status"] == RouteStatus.DATA_UNAVAILABLE.value
    assert res["no_safe_route"] is None
    
    # limit 문구가 센서 없음을 명확히 설명하는지
    assert "센서" in res["limit"]
    
    jsonschema.validate(instance=res, schema=safe_route_schema)

def test_not_required_schema(real_safe_points, real_sensors, official_0808, safe_route_schema):
    provider = DesignatedPointRouteProvider(safe_points=real_safe_points, sensors=real_sensors)
    origin = RoutePoint(lat=37.4979, lon=127.0276)
    dest = DestinationPoint(id="GN-002", label="신논현역", lat=37.5045, lon=127.0250)
    
    req = RouteRequest(
        primary_action=Action.WAIT,
        origin=origin,
        destination=dest,
        asof="2022-08-08T21:40:00+09:00",
        official=official_0808
    )
    
    res = provider.solve(req)
    assert res["status"] == RouteStatus.NOT_REQUIRED.value
    jsonschema.validate(instance=res, schema=safe_route_schema)

def test_destination_blocked_schema(real_safe_points, real_sensors, safe_route_schema):
    provider = DesignatedPointRouteProvider(safe_points=real_safe_points, sensors=real_sensors)
    origin = RoutePoint(lat=37.4979, lon=127.0276)
    dest = DestinationPoint(id="GN-002", label="신논현역", lat=37.5045, lon=127.0250)
    
    req = RouteRequest(
        primary_action=Action.MOVE,
        origin=origin,
        destination=dest,
        asof="2022-08-08T21:40:00+09:00",
        official={"closures": [{"blocks_destination_ids": ["GN-002"]}]}
    )
    
    res = provider.solve(req)
    assert res["status"] == RouteStatus.DESTINATION_BLOCKED.value
    assert res["no_safe_route"] is None
    jsonschema.validate(instance=res, schema=safe_route_schema)

def test_no_safe_point_schema(real_safe_points, real_sensors, safe_route_schema):
    provider = DesignatedPointRouteProvider(safe_points=real_safe_points, sensors=real_sensors)
    origin = RoutePoint(lat=37.4979, lon=127.0276)
    dest = DestinationPoint(id="GN-002", label="신논현역", lat=37.5045, lon=127.0250)
    
    sp_ids = [p["id"] for p in real_safe_points]
    
    req = RouteRequest(
        primary_action=Action.EVACUATE,
        origin=origin,
        destination=dest,
        asof="2022-08-08T21:40:00+09:00",
        official={"closures": [{"blocks_destination_ids": sp_ids}]}
    )
    
    res = provider.solve(req)
    assert res["status"] == RouteStatus.NO_SAFE_POINT.value
    assert res["route_attempted"] is False
    assert res["no_safe_route"] is None
    jsonschema.validate(instance=res, schema=safe_route_schema)
