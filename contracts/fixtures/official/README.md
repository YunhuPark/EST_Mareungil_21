# 공식정보 픽스처

`CT-05`. 2022-08-08 공식 경보·대피 지시·도로 통제를 담는다.
스키마는 [`../../schema/official_info.schema.json`](../../schema/official_info.schema.json).

## 지금 상태

| 파일 | 상태 | 소유자 | 기한 |
|---|---|---|---|
| `official_0808.json` | **DRAFT_UNVERIFIED — 형식만 확정, 값 비어 있음** | 기획 PM | G0 (T+1:30) |

값이 비어 있는 것은 실수가 아니다. **원출처를 확인하기 전에 경보 시각을 지어내지 않는다.**
`verification: "DRAFT_UNVERIFIED"` 가 붙어 있는 동안 이 파일의 내용을 발표나 화면에서
"공식 확인된 사실"로 표현하지 않는다.

## 이 픽스처가 정하는 것

이 파일 하나가 아래를 동시에 결정하므로 G0 에서 가장 먼저 채워야 한다.

- **데모 시각.** 설계서 13.2 의 20:00·20:10·20:20·20:40·20:55 는 초안이다.
  확정 시각은 이 파일의 `asof` 이고, UI 는 언제나 응답의 `clock.label` 을 쓴다.
- **`EVACUATE` 발화 시점.** `evacuation_order: true` 는 행동 우선순위 4를 켠다.
  내부 강우·하수 데이터가 없어도 이 값은 살아남는다(R5-c).
- **`DS-S6` 목적지 차단.** `closures[].blocks_destination_ids` 와
  `confirmed_flooding[].blocks_destination_ids` 가 `DESTINATION_BLOCKED` 의
  **유일한** 근거다. AI 예측 확률로는 목적지를 차단하지 않는다(RT-17).
- **경로 후보 제외.** 통제 구간은 후보 비교 **전에** 빠진다. 통제 자체가 행동을
  `EVACUATE` 로 바꾸지는 않는다(RT-11, C-30).

## 채울 때 주의

- `mode: "VEHICLE"` 은 보행 차단으로 승격하지 않는다. 위험 가중만 올리고
  사유에 "차량 통제 구간"으로 적는다.
- 경보 해제(`cleared_at`)만을 이유로 높은 AI 위험을 낮추지 않는다(F-14).
- 시간은 ISO 8601 에 시간대를 붙인다 (`+09:00`).
