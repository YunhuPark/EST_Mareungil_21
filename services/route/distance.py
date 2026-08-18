import math

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 위경도 좌표(도 단위) 사이의 거리를 미터(m) 단위로 반환한다.
    
    기존 `scripts/mareungil/area_risk.py`의 거리 계산식과 동일한
    구면코사인법칙/하버사인 공식(반경 6371km)을 사용하며,
    순수 함수로서 어떠한 외부 상태나 I/O에도 의존하지 않는다.
    
    Args:
        lat1: 첫 번째 지점의 위도
        lon1: 첫 번째 지점의 경도
        lat2: 두 번째 지점의 위도
        lon2: 두 번째 지점의 경도
        
    Returns:
        두 지점 사이의 대원 거리 (m)
    """
    if lat1 == lat2 and lon1 == lon2:
        return 0.0
        
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlam / 2) ** 2
    
    # 부동소수점 오차로 범위를 초과하는 경우 방지
    if a > 1.0:
        a = 1.0
    elif a < 0.0:
        a = 0.0
        
    return 2 * radius * math.asin(math.sqrt(a))
