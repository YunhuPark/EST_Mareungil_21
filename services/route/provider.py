from typing import Any, Optional
from services.route.interface import RouteProvider, RouteRequest
from services.decision.enums import Action, RouteStatus, RouteTarget
from services.route.distance import haversine_m

class DesignatedPointRouteProvider(RouteProvider):
    def __init__(self, safe_points: list[dict[str, Any]], sensors: list[dict[str, Any]]):
        self.safe_points = safe_points
        self.sensors = sensors

    def _get_route_target(self, action: Action) -> Optional[str]:
        if action == Action.MOVE:
            return RouteTarget.USER_DESTINATION.value
        elif action == Action.EVACUATE:
            return RouteTarget.SAFE_POINT.value
        return None

    def solve(self, request: RouteRequest) -> dict[str, Any]:
        route_target = self._get_route_target(request.primary_action)

        # 1. NOT_REQUIRED 처리
        if request.primary_action in (Action.WAIT, Action.EMERGENCY, Action.UNAVAILABLE):
            return {
                "status": RouteStatus.NOT_REQUIRED.value,
                "route_target": None,
                "target": None,
                "route_attempted": False,
                "no_safe_route": None,
                "route_verified": False,
                "limit": "경로 탐색이 필요하지 않은 행동입니다."
            }

        # 2. 공식 통제로부터 차단된 목적지/거점 ID 목록 수집
        blocked_ids = set()
        official = request.official
        for key in ("closures", "confirmed_flooding"):
            for item in official.get(key, []):
                for b_id in item.get("blocks_destination_ids", []):
                    blocked_ids.add(b_id)

        # 3. 유효 센서 필터링
        valid_sensors = []
        for s in self.sensors:
            try:
                lat = float(s["location"]["lat"])
                lon = float(s["location"]["lon"])
                p = float(s["horizons"]["30"]["high_level_p"])
                valid_sensors.append({"lat": lat, "lon": lon, "risk": p})
            except (KeyError, TypeError, ValueError):
                continue

        # 유효 센서가 하나도 없으면 DATA_UNAVAILABLE 반환
        if not valid_sensors and request.primary_action == Action.EVACUATE:
            return {
                "status": RouteStatus.DATA_UNAVAILABLE.value,
                "route_target": route_target,
                "target": None,
                "route_attempted": False,
                "no_safe_route": None,
                "route_verified": False,
                "limit": "유효한 좌표와 30분 위험 확률을 함께 가진 센서가 없어 후보 간 상대 위험을 판단할 수 없습니다."
            }

        if request.primary_action == Action.MOVE:
            dest_id = request.destination.id
            if dest_id in blocked_ids:
                return {
                    "status": RouteStatus.DESTINATION_BLOCKED.value,
                    "route_target": route_target,
                    "target": None,
                    "route_attempted": False,
                    "no_safe_route": None,
                    "route_verified": False,
                    "limit": "공식 정보에 의해 명시적으로 차단된 목적지입니다."
                }
            else:
                return {
                    "status": RouteStatus.FALLBACK_CANDIDATE.value,
                    "route_verified": False,
                    "route_target": route_target,
                    "target": {
                        "kind": "DESTINATION_POINT",
                        "id": dest_id,
                        "label": request.destination.label,
                        "lat": request.destination.lat,
                        "lon": request.destination.lon
                    },
                    "route_attempted": True,
                    "no_safe_route": False,
                    "distance_m": haversine_m(request.origin.lat, request.origin.lon, request.destination.lat, request.destination.lon),
                    "eta_sec": None,
                    "profile_applied": [],
                    "limit": "지정 지점에 대한 점대점 비교 결과이며 실제 통행 가능성이나 안전을 보장하지 않습니다."
                }

        elif request.primary_action == Action.EVACUATE:
            candidates = []
            for sp in self.safe_points:
                if sp["id"] in blocked_ids:
                    continue
                
                nearest_risk = None
                min_dist = float('inf')
                for s in valid_sensors:
                    dist = haversine_m(sp["lat"], sp["lon"], s["lat"], s["lon"])
                    if dist < min_dist:
                        min_dist = dist
                        nearest_risk = s["risk"]
                        
                origin_dist = haversine_m(request.origin.lat, request.origin.lon, sp["lat"], sp["lon"])
                
                candidates.append({
                    "sp": sp,
                    "risk": nearest_risk if nearest_risk is not None else 0.0,
                    "dist": origin_dist
                })

            if not candidates:
                return {
                    "status": RouteStatus.NO_SAFE_POINT.value,
                    "route_target": route_target,
                    "target": None,
                    "route_attempted": False,
                    "no_safe_route": None,
                    "route_verified": False,
                    "limit": "모든 안전거점이 공식 정보에 의해 차단되었습니다."
                }

            candidates.sort(key=lambda x: (x["risk"], x["dist"], x["sp"]["id"]))
            
            best = candidates[0]
            return {
                "status": RouteStatus.FALLBACK_CANDIDATE.value,
                "route_verified": False,
                "route_target": route_target,
                "target": {
                    "kind": "SHELTER",
                    "id": best["sp"]["id"],
                    "label": best["sp"]["label"],
                    "lat": best["sp"]["lat"],
                    "lon": best["sp"]["lon"]
                },
                "route_attempted": True,
                "no_safe_route": False,
                "distance_m": best["dist"],
                "eta_sec": None,
                "profile_applied": [],
                "limit": "공식 대피시설 후보의 상대 비교 결과이며 실제 통행 가능성이나 안전을 보장하지 않습니다."
            }
        
        return {
            "status": RouteStatus.NOT_REQUIRED.value,
            "route_target": None,
            "target": None,
            "route_attempted": False,
            "no_safe_route": None,
            "route_verified": False,
            "limit": "알 수 없는 행동입니다."
        }
