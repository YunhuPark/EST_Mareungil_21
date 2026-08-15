# 계약 스키마

JSON Schema **Draft 2020-12**. 이 디렉터리가 모든 enum·필드의 **정본**이다.

## 4대 계약 + 공식정보

| 파일 | 방향 | 값 소유 | 무엇이 검증하나 |
|---|---|---|---|
| `risk_assessment.schema.json` | ① 예측 AI → ② 판단 엔진 | E · 안윤지 | `risk_*.json` 5개 + `demo/` 합성 검증 |
| `action_decision.schema.json` | ② 판단 엔진 → ③ 경로 엔진 | B · 유진희 | `decision/` 픽스처 |
| `safe_route.schema.json` | ③ 경로 엔진 → ② 판단 엔진 | C · 김윤후 | `demo/` 합성 검증 + `invalid/` |
| `assess_response.schema.json` | 통합 API → ④ UI | B · 유진희 | `demo/` 픽스처 |
| `official_info.schema.json` | 픽스처 → ② | PM · 안려현 | `official/` 픽스처 |

**스키마 파일 자체는 계약 오너(A · 안윤지) 1명만 고친다.** 값 소유자는 그 계약에 실리는
값을 책임지는 사람이고, 스키마 구조를 직접 고치지 않는다.

**모든 계약은 자신을 검증하는 픽스처를 가져야 한다.** 오른쪽 열이 비면 그 계약은
있는 척만 하는 문서다 — 실제로 `action_decision` 이 G0 전까지 그런 상태였다.
`tests/test_contracts.py` 의 `test_모든_계약이_적어도_하나의_픽스처로_검증된다` 가 이것을 강제한다.

## 합성 검증 — `$ref` 를 쓰지 않는 이유

`AssessResponse` 는 안에 `RiskAssessment`(`risk`)와 `SafeRoute`(`route`)를 담는다.
보통은 `$ref` 로 잇지만 여기서는 **각 블록을 해당 스키마로 따로 한 번 더 검증**한다.

기존 `$id` 가 `mareungil/risk_assessment@v1` 같은 **상대 URI** 라서 `$ref` 해석 결과가
도구마다 달라진다. 합성 검증은 같은 보장을 주면서 계약 파일을 각각 독립적으로 열 수
있게 둔다. 소유 관계는 `contracts/validate.py` 의 `COMPOSED_BLOCKS` 한 곳에만 적혀 있다.

따라서 `assess_response.schema.json` 의 `risk`·`route` 는 **얕게** 정의돼 있다.
필수 키만 확인하고, 내부 구조는 각자의 스키마가 본다.

### `decision` 은 합성 검증 대상이 아니다

`ActionDecision` 과 `AssessResponse.decision` 은 **의도적으로 필드가 다르다.**
전자에는 `asof`·`stage`·`official`·`route_prefs` 가 있고, 후자에는 경로 후처리 이후에야
생기는 `primary_action`·`route_postprocess_applied` 가 있다(D-10). 그래서 한쪽을 다른 쪽
스키마로 검사할 수 없고, `COMPOSED_BLOCKS` 에 넣지 않는다.

대신 `contracts/fixtures/decision/` 의 독립 픽스처로 검증한다. 두 스키마의 차이가
의도된 것인지는 [DECISIONS.md](../../docs/DECISIONS.md) 2.1 절의 표가 기록한다.

## 이 스키마들이 실제로 막는 것

계약이 무엇을 보장하는지는 통과 예제가 아니라 **거부 예제**가 증명한다.
`contracts/fixtures/invalid/` 의 6개 파일이 그것이고, 하나라도 통과하면 검증이 실패한다.

아래 표의 "어디서 막나"가 `tests/` 인 항목은 거부 픽스처로 표현할 수 없는 것들이다 —
"픽스처가 없는 계약"처럼 **한 파일의 내용이 아니라 저장소 전체의 상태**를 보는 규칙이다.

| 규칙 | 어디서 막나 |
|---|---|
| `MOVE` 응답에 `NO_SAFE_POINT` (RT-13) | `assess_response` `allOf` |
| `EVACUATE` 응답에 `DESTINATION_BLOCKED` (RT-13) | `assess_response` `allOf` |
| `no_safe_route=true` + `route_attempted=false` (RT-09b) | `safe_route` `allOf` |
| `destination: null` (F-19 / R13) | `assess_response` `$defs.destination` |
| 이름만 `risk_level` 인 필드 (AI-10) | `additionalProperties: false` + `tests/test_contracts.py` |
| `WHEELCHAIR` · `WITH_PET` (C-14) | `profiles` enum |
| 경로 상태의 `UNAVAILABLE` (RT-09) | `route_status` enum 에 없음 |
| `trapped=true` 인데 `EMERGENCY` 아님 (F-05) | `assess_response` `allOf` |
| `MOVE + NO_SAFE_ROUTE` 인데 최종이 `WAIT` 아님 (F-10) | `assess_response` `allOf` |
| 픽스처가 없는 계약 (C-12) | `tests/test_contracts.py` |
| `official_info` 를 `ActionDecision.official` 이 못 받는 상태 (C-11) | `tests/test_contracts.py` |
| `reasons` 4개 이상 (F-03) | 두 스키마 모두 `maxItems: 3` |

### 일부러 막지 **않는** 것

`EVACUATE` 경로 실패, `MOVE + DESTINATION_BLOCKED`, `MOVE + DATA_UNAVAILABLE` 의
**최종 행동은 강제하지 않는다.** 안전정책이 아직 `OPEN` 이기 때문이다
([DECISIONS.md](../../docs/DECISIONS.md) O-02~O-05).

스키마가 값을 강제하면 그게 곧 정책 확정이 된다. 정하지 않은 것은 비워 둔다.

## `_` 로 시작하는 필드

주석·출처·경고를 담는 **주석 네임스페이스**다. `patternProperties: {"^_": {}}` 로 허용한다.

```json
{ "_stub": "services/route 미구현. 후보 비교 결과가 아니다." }
```

`additionalProperties: false` 는 그대로 살아 있으므로 오타난 필드는 여전히 걸린다.

## 바꿀 때

1. **먼저 기존 스키마를 읽는다.** 통째로 교체하지 않는다.
2. 기존 픽스처가 깨지는지 확인한다 — `.\make.ps1 contracts`
3. 네 곳을 **같은 커밋에서** 고친다: 스키마 · 픽스처 · 테스트 · `web/src/contracts/`
4. [DECISIONS.md](../../docs/DECISIONS.md) 에 한 줄 남긴다
5. **enum 과 `required` 변경은 G3 이후 금지**

### 하위호환을 위해 남겨둔 것

| 필드 | 상태 | 언제 정리하나 |
|---|---|---|
| `area_risk.score` | `DEPRECATED`. `risk_probability` 의 예전 이름 | 픽스처 생성기 갱신 후 (O-01 이 닫히면 재생성이 필요하므로 그때 함께) |
| `risk_probability`, `ai_risk_level`, `threshold_version` | optional | 같은 시점에 `required` 승격 |

`required` 로 먼저 올리면 기존 RF 픽스처 5개가 전부 깨지고, 되살리려면 모델을
다시 학습해야 한다. 그래서 optional 로 두고 새 픽스처에만 채웠다.
