# 거부 예제

**이 파일들은 계약 검증에 실패해야 한다.** 통과하면 `.\make.ps1 contracts` 가 실패한다.

계약이 무엇을 보장하는지는 통과 예제가 아니라 거부 예제가 증명한다.
"`MOVE` 에 `NO_SAFE_POINT` 가 오면 안 된다"고 문서에 쓰는 것과, 그런 payload 를
실제로 만들어서 스키마가 막는 걸 보는 것은 다르다.

## 파일

| 파일 | 대상 스키마 | 규칙 |
|---|---|---|
| `move_with_no_safe_point.json` | `assess_response` | RT-13 · F-10 |
| `evacuate_with_destination_blocked.json` | `assess_response` | RT-13 · F-10 |
| `no_safe_route_without_attempt.json` | `safe_route` | RT-09b |
| `destination_null.json` | `assess_response` | F-19 · R13 |
| `ambiguous_risk_level.json` | `assess_response` | AI-10 · 설계서 6.1 |
| `profile_wheelchair.json` | `assess_response` | X1 · C-14 |
| `severe_without_direct_signal.json` | `assess_response` | C-23 (AI 만으로 `SEVERE` 불가) |
| `evacuate_route_failure_escalated.json` | `assess_response` | M-15 · C-31 (경로 실패로 `EMERGENCY` 승격 금지) |
| `move_destination_blocked_switched_to_wait.json` | `assess_response` | M-16 (목적지 차단 ≠ 안전경로 없음) |
| `expired_without_stale.json` | `assess_response` | M-08 (신선도 10분·30분은 포함 관계) |

## 형식

각 파일이 스스로 무엇을 검사받을지 선언한다.

```json
{
  "_expect_invalid": {
    "schema": "assess_response",
    "rule": "RT-13 / F-10",
    "why": "MOVE 응답에 NO_SAFE_POINT 가 실렸다"
  },
  "...": "나머지는 그 하나만 빼면 유효한 payload"
}
```

**나머지 필드는 유효하게 둔다.** 여러 곳이 동시에 틀려 있으면 어느 규칙이 막았는지
알 수 없어서, 규칙이 사라져도 테스트가 계속 통과해버린다.

## 재생성

```powershell
.\make.ps1 fixtures
```

`scripts/build_demo_assess_fixtures.py` 의 `_invalid_cases()` 가 `DS-S1` 에서
한 곳씩만 바꿔 만든다. `DS-S1` 이 바뀌면 이 파일들도 함께 따라간다.

파일 크기를 줄이려고 `risk` 블록은 무데이터 픽스처(`RF-E1`)로 바꿔 넣었다.
`RF-E1` 자체는 스키마를 통과하므로 남는 위반은 각 예제가 의도한 하나뿐이다.

## 새 거부 예제를 추가할 때

1. `_invalid_cases()` 에 항목을 넣는다
2. `.\make.ps1 fixtures` 로 생성
3. `.\make.ps1 contracts` 로 **거부되는지** 확인
4. 필수 조합이면 `tests/test_contracts.py` 의 `test_거부_예제가_요구된_조합을_모두_덮는다` 에도 추가
