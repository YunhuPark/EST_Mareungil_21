# 공식정보 픽스처

`CT-05`. 2022-08-08 공식 경보·대피 지시·도로 통제를 담는다.
스키마는 [`../../schema/official_info.schema.json`](../../schema/official_info.schema.json).

## 지금 상태

| 파일 | `verification` | 무엇인가 |
|---|---|---|
| `official_0808.json` | **`VERIFIED_SOURCE`** | O-11 로 원출처를 확인한 실제 값 |
| `official_demo_destination_blocked.json` | **`DEMO_FIXTURE`** | `DS-S6` 시연용 **합성** 통제 하나 |
| `sources/2022-08-08_gangnam_verified_events.csv` | — | 원문 대조표 30건. 위 실제 값의 출처 |

**두 파일을 합치지 않는다.** `verification` 은 파일 단위 단일 값이라, 지어낸
통제를 실제 값 파일에 넣으면 그것이 확인된 사실로 읽힌다(M-24·M-36).

## 왜 시연용 파일이 따로 필요한가

M-16 이 확정한 `MOVE` + `DESTINATION_BLOCKED` 화면을 보여주려면 목적지를 막는
공식 통제가 하나 필요하다. **그런데 확인된 실제 자료에는 그런 것이 없다.**

- 그날 강남 도로 통제 보도는 **전부 22:01 이후 송고**됐다. 확정 재생 시각
  21:40 에는 아직 공개돼 있지 않았으므로 판단에 쓸 수 없다(M-36).
- 확인된 통제 6건 중 강남역 반경 1km 안은 강남대로 하위 4개 차로 하나뿐이고,
  그것은 **차량 통제**라 보행 목적지를 막지 못한다(RT-11).

숨기지 말고 발표에서 그대로 말한다 — 이건 데이터 누락이 아니라 **당시 시민이 알
수 있던 것의 실제 범위**다.

## `available_time` 규칙 (M-36)

`available_time` 은 **공개시각**이고 `issued_at`·`since`·`observed_at` 은
**발생·관측시각**이다. 재생 시각보다 공개시각이 빠르거나 같은 항목만 판단에 쓴다.

| 종류 | `available_time` 에 무엇을 넣나 |
|---|---|
| 기상·홍수 특보 | **발효시각.** 특보는 발효와 동시에 공표된다 |
| 도로 통제 · 확인 침수 | **언론 송고시각.** 확인 가능한 가장 이른 공개 시점이다 |
| 그 밖에 확인 못 한 것 | `null`. **지어내지 않는다.** 이 항목은 판단에서 빠진다 |

필터 구현은 `services/decision/official.py` **하나뿐**이고,
`scripts/build_demo_assess_fixtures.py` 의 `official_at()` 이 그것을 부른다.
UI 는 다시 거르지 않는다 — 두 곳에서 시각을 판정하면 화면과 판단이 어긋난다.

## 이 픽스처가 정하는 것

- **`EVACUATE` 발화 시점.** `evacuation_order: true` 는 행동 우선순위 4를 켠다.
  내부 강우·하수 데이터가 없어도 이 값은 살아남는다(R5-c).
  현재 값은 `false` 이며, **그것이 "대피명령이 없었다"는 단정은 아니다** —
  원출처가 대피 사실만 확인해 주고 명령 발령 여부는 말하지 않는다. 파일의
  `_evacuation_order_note` 참조.
- **`DS-S6` 목적지 차단.** `closures[].blocks_destination_ids` 와
  `confirmed_flooding[].blocks_destination_ids` 가 `DESTINATION_BLOCKED` 의
  **유일한** 근거다. AI 예측 확률로는 목적지를 차단하지 않는다(RT-17).
- **경로 후보 제외.** 통제 구간은 후보 비교 **전에** 빠진다. 통제 자체가 행동을
  `EVACUATE` 로 바꾸지는 않는다(RT-11, C-30).

## 채울 때 주의

- `mode: "VEHICLE"` 은 보행 차단으로 승격하지 않는다. 위험 가중만 올리고
  사유에 "차량 통제 구간"으로 적는다. 2022-08-08 자료는 보행 통제 여부를 거의
  남기지 않았으므로 화면 문구가 그 차이를 그대로 말한다.
- 경보 해제(`cleared_at`)만을 이유로 높은 AI 위험을 낮추지 않는다(F-14).
- `confirmed_flooding[].observed_at` 은 **`null` 을 허용하지만 필드를 빼지는
  않는다**(C-24). `null` 은 "관측 시각을 확인하지 못했다"이고 키가 없는 것은
  "그런 항목을 생각하지 않았다"다. 거부 예제가
  [`../invalid/flooding_without_observed_at.json`](../invalid/flooding_without_observed_at.json).
- 시간은 ISO 8601 에 시간대를 붙인다 (`+09:00`).
- 통제·침수는 계약을 타고 **화면에 그대로 찍힌다.** `label` 문구도
  `tests/test_forbidden_wording.py` 의 금칙어 검사를 받는다.
