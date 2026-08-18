# 경로 모듈 통합 인계서 (API 담당자용)

박윤후 담당 경로 모듈(`DesignatedPointRouteProvider`) 구현이 완료되었습니다. API 및 Decision Engine 통합 시 아래 사항을 준수하여 연결해 주시기 바랍니다.

## 1. Import 경로
```python
from services.route.provider import DesignatedPointRouteProvider
from services.route.interface import RouteRequest, RoutePoint, DestinationPoint
from services.decision.enums import Action
```

## 2. 안전거점 및 센서 데이터 로드 (생성자 인자)
Provider는 파일 I/O를 직접 수행하지 않습니다. API 조립 단계에서 로드하여 주입해 주세요.

### 안전거점 7곳 로드
`contracts/safe_points.json`을 읽어 리스트로 주입합니다.
```python
import json
with open("contracts/safe_points.json", "r", encoding="utf-8") as f:
    safe_points = json.load(f)
```

### RiskAssessment 센서 배열 전달
현재 재생 시각(`asof`)에 해당하는 `RiskAssessment` 산출물의 `area_risk.sensors` 배열을 추출하여 주입합니다. 만약 센서 데이터가 없으면 빈 리스트를 주입합니다.
```python
# risk_assessment는 현재 시각에 유효한 모델 산출물 (dict)
sensors = risk_assessment.get("area_risk", {}).get("sensors", [])

provider = DesignatedPointRouteProvider(
    safe_points=safe_points,
    sensors=sensors
)
```

## 3. RoutePoint 및 RouteRequest 생성 예제
`RouteRequest`에 사용자 현재 위치를 위한 `origin: RoutePoint` 필드가 추가되었습니다.

```python
# 사용자 위치 (예: 강남역)
origin = RoutePoint(lat=37.4979, lon=127.0276)

# 사용자가 선택한 목적지
destination = DestinationPoint(
    id="GN-002",
    label="신논현역",
    lat=37.5045,
    lon=127.0250
)

request = RouteRequest(
    primary_action=Action.MOVE, # 또는 Action.EVACUATE
    origin=origin,
    destination=destination,
    asof="2022-08-08T21:40:00+09:00",
    official=official_data # official_info 스키마 형식의 dict
)
```

## 4. `solve()` 호출 예제
```python
result = provider.solve(request)
```

## 5. 상태별 반환 예제

### 성공적인 점대점 비교 (FALLBACK_CANDIDATE)
```json
{
  "status": "FALLBACK_CANDIDATE",
  "route_verified": false,
  "route_target": "SAFE_POINT",
  "target": {
    "kind": "SHELTER",
    "id": "SP-001",
    "label": "서초초등학교",
    "lat": 37.49952,
    "lon": 127.02393
  },
  "route_attempted": true,
  "no_safe_route": false,
  "distance_m": 370.5,
  "eta_sec": null,
  "profile_applied": [],
  "limit": "공식 대피시설 후보의 상대 비교 결과이며 실제 통행 가능성이나 안전을 보장하지 않습니다.",
  "candidates": []
}
```

### 목적지 명시적 차단 (DESTINATION_BLOCKED)
```json
{
  "status": "DESTINATION_BLOCKED",
  "route_target": "USER_DESTINATION",
  ...
}
```

### 거점 전체 차단 (NO_SAFE_POINT) / 센서 데이터 없음 (DATA_UNAVAILABLE)
```json
{
  "status": "NO_SAFE_POINT", # 또는 "DATA_UNAVAILABLE"
  "route_target": "SAFE_POINT",
  "target": null,
  ...
}
```

## 6. Decision Engine 후처리 규칙
- **NO_SAFE_ROUTE 미생성**: 이번 LIVE Provider는 실제 완결 경로 탐색을 하지 않으므로 `NO_SAFE_ROUTE`를 반환하지 않습니다.
- **WAIT 전환**: `MOVE + NO_SAFE_ROUTE → WAIT` 전환 규칙은 기존 FIXTURE 또는 실제 경로 엔진의 결과에만 적용됩니다.
- **EMERGENCY 자동 전환 금지**: `EVACUATE` 실패 시(예: `NO_SAFE_POINT`) 이를 `EMERGENCY`로 임의로 변경하지 않습니다. 오직 사용자의 `trapped=true` 입력만 `EMERGENCY`를 유발합니다.

## 7. LIVE / FIXTURE 구분
- `FixtureRouteProvider`: 사전에 정의된 `scenario` 기반으로 고정된 `SafeRoute`를 반환. (과거 테스트용)
- `DesignatedPointRouteProvider`: 실시간(LIVE)으로 센서 데이터, 사용자 위치, 공식정보를 비교하여 결정론적으로 후보를 산출합니다. 향후 API에 실제 사용자 데이터가 들어오면 이 클래스를 사용해야 합니다.

## 8. 계약 부채 (Contract Debt)
1. **FALLBACK_CANDIDATE 및 route_attempted**: `status=FALLBACK_CANDIDATE` 시 스키마가 `route_attempted=true`를 강제하고 있습니다. 이번 구현은 단순 지점 비교이므로 실제 경로를 탐색(attempt)한 것이 아니나, 스키마 유효성을 위해 `true`로 반환합니다. 이 부분은 향후 의미 분리가 필요합니다.
2. **candidates 배열**: `SafeRoute` 계약상 공식 대피경로 후보 목록을 넣도록 되어 있으나, 이번 버전에선 사용하지 않으므로 빈 배열(`[]`)을 반환합니다. (안전거점을 억지로 `route_id`에 부여하지 않음)

## 9. 오류 처리
Provider 내부는 예외를 던지지 않도록 작성되었으며, 비정상적 액션 요청 시 `status=NOT_REQUIRED`를 반환합니다. 센서 형식이 잘못되었거나 누락된 경우 유효 센서가 0개가 되어 `status=DATA_UNAVAILABLE`로 우아하게 실패합니다.

## 10. UI 노출 주의사항 (금지 표현 및 값 의미)
- 결과로 도출된 `SP-006` 등을 무조건적으로 안전이 확보된 시설이나 경로라고 절대 표현하지 마세요. 공식 통제와 센서의 30분 위험 신호, 거리를 기준으로 상대 비교한 대피시설 후보일 뿐이며 실제 통행 가능성이나 안전을 보장하지 않습니다.
- 선택된 대상의 `relative_risk=0.9988` 등은 절대적인 시설 침수 확률이 아니라 **최근접 하수 센서의 30분 고수위 확률을 후보 비교 근거로 사용한 값**일 뿐이므로 사용자 UI에 시설 자체의 침수 확률로 표시하지 않도록 주의해야 합니다.
