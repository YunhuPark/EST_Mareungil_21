"""서비스 위험 등급 판정 — 축 1 (`service_risk_level`).

`SAFE` / `CAUTION` / `DANGER` / `SEVERE` 를 정한다. **행동(`action`)을 정하지 않는다.**

두 축을 따로 두는 이유
----------------------
같은 `DANGER` 라도 사용자가 안전한 실내에 있으면 `WAIT`, 실외에 있으면
`EVACUATE` 다. 등급을 행동 결정의 중간값으로 두면 그 차이를 등급 안에
숨겨야 하고, 그러면 화면에 찍히는 "위험합니다"와 "지금 무엇을 하세요"가
서로를 설명하지 못한다. 그래서 **같은 입력에서 두 값을 각각 산출**한다.

    service_risk_level  <- 이 모듈            (지금 얼마나 위험한가)
    action              <- 설계서 9장 우선순위 1~10  (지금 무엇을 해야 하는가)

등급과 행동을 1:1 로 잇는 표를 만들지 않는다. 매핑이 필요해 보이면 그건
둘 중 하나가 입력을 덜 보고 있다는 뜻이다.

`DATA_UNAVAILABLE` 은 등급이 아니다
-----------------------------------
데이터 지연·결측·범위 밖은 **데이터 상태**이며 위험 등급 축에 넣지 않는다
(`DataState`). 다만 "판단할 근거가 없다"를 `SAFE` 라고 말할 수는 없으므로
**등급의 하한을 `CAUTION` 으로 올린다.** 그리고 공식 대피 지시나 고립 신고
같은 직접 안전신호는 데이터가 없어도 그대로 적용된다 — 자기신고와 공식
지시는 내부 강우·하수·AI 데이터와 독립이기 때문이다(설계서 9장).

규칙
----
- 순수 함수만 둔다. I/O·HTTP·파일 읽기를 하지 않는다(N-04 재현성).
- 새 기준값을 만들지 않는다. 여기 있는 수는 전부 설계서 9.1·9.2 의 확정값이며
  출처를 상수 주석에 적었다(CLAUDE.md 9절).
- **이 모듈에 남은 미확정 항목은 없다.** O-15(추가 위험신호 집합)가
  2026-08-16 에 닫혔다 — 아래 `_additional_signals()` 위 주석 참조.
"""

from __future__ import annotations

from dataclasses import dataclass

from services.decision.enums import (
    AiRiskLevel,
    Basis,
    HazardSign,
    ServiceRiskLevel,
    UserContext,
)

# --- 확정 기준값 -------------------------------------------------------------
#
# 전부 이미 합의된 값이며 이 모듈이 새로 고른 수는 하나도 없다.

#: TH-02. 60분 누적 강우(mm). 설계서 9.2 확정값이며 45개 사건 중 6개에서 걸린다.
RAIN_60M_MM = 40.0

#: DQ-01 / M-08. 데이터 지연 상한(초). 10분 초과면 **행동을 바꾸지 않고** 지연만 표시한다.
STALE_SEC = 600

#: M-08. 판단 근거 제외 상한(초). 30분을 넘긴 자료는 등급 산출에서 뺀다.
#:
#: **20분 단계는 없다.** 회의에서 "10분·30분 기준으로 단순화한다"로 삭제했으므로
#: 여기에 중간 단계를 만들지 않는다.
EXPIRED_SEC = 1800

#: DQ-03. 센서 관측률 하한. 설계서 9.1 — 70% 미만이면 품질 저하.
OBSERVED_RATE_MIN = 0.70

#: F-03. 화면에 싣는 사유 상한. 계약도 같은 상한을 건다.
MAX_REASONS = 3


# --- DANGER 의 추가 위험신호 — 확정 (O-15, 2026-08-16) -----------------------
#
# **등급 축에서 세는 추가 위험신호는 TH-02 하나뿐이다.**
#
# TH-01 을 왜 등급 축에 넣지 않나
# -------------------------------
# TH-01(10분 >= 5mm)과 TH-02(60분 >= 40mm)를 **OR 로 묶는 것은 확정**이다
# (요구사항 정의서 167 · 설계서 9.2 · 회귀 케이스 R14). 다만 그 확정은
# **행동 축**(규칙 9 -> WAIT)에 대한 것이고, 등급 축이 같은 묶음을 재사용할지는
# 따로 정해야 했다. 재사용하지 않기로 했다.
#
# 발화 빈도가 다르다. `data_unified/processed/v2/event_windows.csv` 의 강우 사건
# 22개(전체 45개 중 DRY 23개 제외) 기준:
#
#     TH-02  60분 >= 40mm    6개  (27%)
#     TH-01  10분 >=  5mm   14개  (64%)   <- 2.3배
#
# AI 가 HIGH 인 시점은 대체로 비가 세게 오는 시점이라, 등급 축에서 OR 를 그대로
# 쓰면 **DANGER 가 사실상 AI HIGH 와 같아진다.** 그러면 조합표(DECISIONS 2.2.1)의
# `CAUTION` + `HIGH 단독` 행이 비고, 등급을 네 단계로 나눈 이유가 사라진다 —
# DANGER 가 "복합 위험"이라는 말이 성립하려면 AI 보다 선택적인 신호여야 한다.
#
# **같은 신호가 두 축에서 다른 무게를 갖는 것이 C-23 의 요점이다.** TH-01 은
# "지금 움직이지 마라"를 만들기엔 충분하지만 "여러 신호가 동시에 확인됐다"를
# 말하기엔 흔하다. 그래서 행동 축에서는 여전히 WAIT 을 만들고(규칙 9), 등급 축에서는
# 세지 않는다. 화면에 `CAUTION` + `WAIT` 이 함께 나오는 것은 의도된 조합이다.
#
# 하수 부담을 왜 세지 않나
# ------------------------
# TH-05(하수 고수위)는 이미 `ai_risk_level` 을 통해 들어와 있다. 설계서 9.2 가
# "TH-05 는 규칙 9 에서 다시 세지 않는다"고 정해 뒀고, 이것을 추가 신호로 다시
# 세면 **같은 축을 두 번 세는 것**이 되어 "복합 위험"이 성립하지 않는다. 독립
# 신호로 쓰려면 `ai_risk_level` 과 무관한 하수 지표와 임계가 필요한데 저장소에
# 근거가 없다.
#
# 새 수는 하나도 만들지 않았다. 확정값 TH-02 를 어디에 쓸지만 정했다.


@dataclass(frozen=True)
class Reason:
    """판정 사유 한 줄. 계약의 `reasons[]` 항목과 같은 모양이다."""

    code: str
    text: str
    basis: Basis
    value: float | str | None = None
    threshold: float | str | None = None

    def as_dict(self) -> dict:
        return {
            "code": self.code,
            "text": self.text,
            "value": self.value,
            "threshold": self.threshold,
            "basis": self.basis.value,
        }


@dataclass(frozen=True)
class DataState:
    """데이터 상태. **위험 등급이 아니다.**

    `DATA_UNAVAILABLE` 을 등급 축에 섞지 않기 위해 따로 둔다. 계약 필드가
    아니며 응답에 그대로 실리지 않는다 — 등급에 미치는 영향은
    "하한을 CAUTION 으로 올린다" 하나뿐이다.
    """

    delayed: bool = False
    """DQ-01. data_age 가 10분을 넘었다. 표시만 하고 판단은 그대로 간다."""

    expired: bool = False
    """M-08. data_age 가 30분을 넘어 **판단 근거에서 제외**한다.

    제외가 "안전해졌다"로 읽히면 안 된다. 그래서 두 가지를 함께 지킨다.

    - 제외해도 `degraded` 가 참이므로 등급 하한은 `CAUTION` 이다. `SAFE` 로 내려가지 않는다.
    - 직접 안전신호(고립 신고·지하 현장 징후·공식 대피 지시)는 이 축과 독립이라
      그대로 `SEVERE` 를 만든다. 낡은 것은 내부 관측 자료이지 자기신고가 아니다.

    잃는 것은 **`DANGER` 뿐이다** — 30분 지난 자료로 "복합 위험이 지금 있다"고
    말할 수 없기 때문이다. 행동 쪽에서는 우선순위가 `MOVE → WAIT` 으로 받는다(M-08).
    """

    quality_low: bool = False
    """DQ-03. 센서 관측률이 70% 미만이다."""

    ai_unavailable: bool = False
    """area_risk.ai_risk_level 이 null 이다. 0 으로 채우지 않는다."""

    rain_unavailable: bool = False
    """data_quality.rain_available 이 false 다."""

    out_of_service_area: bool = False
    """우선순위 3. 서비스 범위 밖이다."""

    @property
    def degraded(self) -> bool:
        """하나라도 정상이 아니면 참. 등급 하한을 CAUTION 으로 올린다."""
        return any(
            (
                self.delayed,
                self.expired,
                self.quality_low,
                self.ai_unavailable,
                self.rain_unavailable,
                self.out_of_service_area,
            )
        )


@dataclass(frozen=True)
class RiskSignals:
    """`classify()` 의 입력. 전부 계약에서 그대로 읽을 수 있는 값이다.

    어디서 오는지:

    ==============================  ==========================================
    필드                             출처
    ==============================  ==========================================
    context·trapped·hazard_signs    AssessResponse.decision.user_state
    evacuation_order·closure_count  AssessResponse.official
    alerts_all_cleared              AssessResponse.official.alerts[].cleared_at
    ai_risk_level                   AssessResponse.risk.area_risk
    data_age_sec                    AssessResponse.clock
    observed_rate·rain_available    AssessResponse.risk.data_quality
    rain_past_60m_mm                AssessResponse.risk.drivers[]
    in_service_area                 AssessResponse.location
    ==============================  ==========================================
    """

    context: UserContext

    # --- 자기신고. AI·강우·하수 데이터와 독립이며 데이터 단절이 덮지 못한다 ---
    trapped: bool = False
    hazard_signs: tuple[HazardSign, ...] = ()

    # --- 공식정보. 위험도의 하한이며 AI 가 낮출 수 없다(F-14) ---
    official_present: bool = False
    """공식정보 블록을 받았는가. **등급을 바꾸지 않는다** - 사유 문구용이다.

    '공식 대피 지시가 없다'와 '공식정보를 못 받았다'는 다른 상태지만, 후자를
    주의 신호로 올리려면 그렇게 정한 근거가 있어야 한다. 지금은 없으므로
    등급에 반영하지 않는다(CLAUDE.md 9절).
    """

    evacuation_order: bool = False

    closure_count: int = 0
    """도로 통제 건수. RT-11 에 따라 **등급을 올리지 않는다.** 통제는 경로
    후보에서 구간을 빼는 데만 쓴다."""

    alerts_all_cleared: bool = False
    """경보가 전부 해제됐는가. F-14 에 따라 **등급을 낮추지 않는다.**"""

    # --- AI. None 은 '산출할 근거가 없다'이며 LOW 와 다르다 ---
    ai_risk_level: AiRiskLevel | None = None

    # --- 데이터 상태 ---
    data_age_sec: int = 0
    observed_rate: float | None = None
    rain_available: bool = True
    rain_past_60m_mm: float | None = None
    in_service_area: bool = True


@dataclass(frozen=True)
class ServiceRiskResult:
    """판정 결과.

    Attributes:
        level: 최종 서비스 위험 등급.
        reasons: 이 등급이 나온 이유. 중요한 순서이며 상한은 `MAX_REASONS` 다.
        data_state: 데이터 상태. 등급 축과 섞지 않는다.

    예전에 `open_policy` 필드가 있었다. O-15 가 닫히면서 **항상 비게 되어**
    없앴다 — 언제나 빈 값인 필드는 "미확정이 있는지"를 더 이상 말해주지 못하고,
    남겨두면 다음 사람이 그걸 채우는 것을 잊었다고 읽는다.
    """

    level: ServiceRiskLevel
    reasons: tuple[Reason, ...]
    data_state: DataState


def _data_state(s: RiskSignals) -> DataState:
    return DataState(
        delayed=s.data_age_sec > STALE_SEC,
        # 30분을 넘겼으면 10분도 넘겼다. 두 단계는 포함 관계이며 계약도 같은 것을 강제한다.
        expired=s.data_age_sec > EXPIRED_SEC,
        quality_low=s.observed_rate is not None and s.observed_rate < OBSERVED_RATE_MIN,
        ai_unavailable=s.ai_risk_level is None,
        rain_unavailable=not s.rain_available,
        out_of_service_area=not s.in_service_area,
    )


def _direct_signals(s: RiskSignals) -> list[Reason]:
    """SEVERE 를 만드는 직접 안전신호.

    셋 다 **AI 확률과 독립**이다. AI 가 `LOW` 여도, AI 값이 아예 없어도
    이 신호가 있으면 높은 판단이 이긴다(공식정보 우선 / F-14).
    """
    found: list[Reason] = []

    if s.trapped:
        found.append(
            Reason(
                "TRAPPED_REPORTED",
                "고립 상태로 신고됐습니다.",
                Basis.TEAM_RULE,
            )
        )

    if s.context is UserContext.UNDERGROUND and s.hazard_signs:
        found.append(
            Reason(
                "UNDERGROUND_HAZARD_SIGN",
                "지하공간에서 현장 위험 징후가 신고됐습니다.",
                Basis.TEAM_RULE,
                # HazardSign 은 StrEnum 이라 계약 JSON 에서 온 맨 문자열도 그대로
                # 들어온다. str() 로 받아 둘 다 통과시킨다.
                value=", ".join(str(sign) for sign in s.hazard_signs),
            )
        )

    if s.evacuation_order:
        found.append(
            Reason(
                "OFFICIAL_EVACUATION_ORDER",
                "이 시각 기준 공식 대피 지시가 있습니다.",
                Basis.OFFICIAL_GUIDANCE,
            )
        )

    return found


def _additional_signals(s: RiskSignals) -> list[Reason]:
    """AI `HIGH` 위에 얹히는 추가 위험신호.

    **TH-02(60분 누적 강우) 하나뿐이며 이것은 확정 규칙이다**(O-15).
    "아직 안 정해서 하나만 센다"가 아니라 "하나만 세기로 정했다"이다.
    TH-01 과 하수 부담을 왜 빼는지는 이 파일 위쪽 O-15 주석에 있다.
    """
    if s.rain_past_60m_mm is not None and s.rain_past_60m_mm >= RAIN_60M_MM:
        return [
            Reason(
                "RAIN_60M_OVER_TH02",
                "60분 누적 강우가 팀 기준값을 넘었습니다.",
                Basis.TEAM_RULE,
                value=s.rain_past_60m_mm,
                threshold=RAIN_60M_MM,
            )
        ]
    return []


def _quality_reasons(state: DataState) -> list[Reason]:
    """데이터 상태를 주의 사유로 옮긴다. 등급 자체를 만들지는 않는다."""
    found: list[Reason] = []

    if state.out_of_service_area:
        found.append(
            Reason(
                "OUT_OF_SERVICE_AREA",
                "서비스 범위 밖이라 이 지역의 위험을 판단할 수 없습니다.",
                Basis.TEAM_RULE,
            )
        )
    if state.ai_unavailable:
        found.append(
            Reason(
                "AI_UNAVAILABLE",
                "지역 위험을 산출할 센서 자료가 없습니다.",
                Basis.AI_PREDICTION,
            )
        )
    # M-08. 두 단계는 포함 관계이므로 사유는 하나만 싣는다. 둘 다 실으면
    # 상한 3줄(F-03) 안에서 더 중요한 사유가 밀려난다.
    if state.expired:
        found.append(
            Reason(
                "DATA_EXPIRED",
                "자료가 기준 시간을 넘겨 이번 판단의 근거에서 제외했습니다.",
                Basis.TEAM_RULE,
                threshold=EXPIRED_SEC,
            )
        )
    elif state.delayed:
        found.append(
            Reason(
                "DATA_DELAYED",
                "자료가 늦게 도착해 지금 상황과 다를 수 있습니다.",
                Basis.TEAM_RULE,
                threshold=STALE_SEC,
            )
        )
    if state.quality_low:
        found.append(
            Reason(
                "DATA_QUALITY_LOW",
                "관측된 센서 비율이 팀 기준 아래입니다.",
                Basis.TEAM_RULE,
                threshold=OBSERVED_RATE_MIN,
            )
        )
    if state.rain_unavailable:
        found.append(
            Reason(
                "RAIN_UNAVAILABLE",
                "강우 자료를 받지 못했습니다.",
                Basis.TEAM_RULE,
            )
        )

    return found


def classify(signals: RiskSignals) -> ServiceRiskResult:
    """서비스 위험 등급을 정한다. 행동은 정하지 않는다.

    첫 일치가 이긴다.

    1. **SEVERE** — 고립 신고 / 지하 + 현장 위험 징후 / 공식 대피 지시.
       즉각적인 안전 대응이 필요한 직접 신호이며 AI 값과 무관하게 이긴다.
    2. **DANGER** — AI `HIGH` **와** 추가 위험신호가 함께 확인된 복합 위험.
    3. **CAUTION** — AI `HIGH` 단독, 또는 데이터 지연·품질 저하 등 주의 신호.
    4. **SAFE** — 직접 신호 없음 + AI `LOW` + 데이터 상태 정상.

    **30분을 넘긴 자료는 AI·강우 축에서 빠진다**(M-08). 빠져도 `SAFE` 로는 내려가지
    않고 `CAUTION` 에 머문다 — 잃는 것은 `DANGER` 뿐이다. 직접 안전신호는 이 축과
    무관하므로 낡은 자료와 함께 사라지지 않는다.

    공식 경보의 **해제**와 도로 **통제**는 등급을 바꾸지 않는다.
    해제만을 이유로 높은 AI 위험을 낮추지 않으며(F-14), 통제는 경로 후보에서
    구간을 빼는 데만 쓴다(RT-11).
    """
    state = _data_state(signals)

    direct = _direct_signals(signals)
    if direct:
        return ServiceRiskResult(
            level=ServiceRiskLevel.SEVERE,
            reasons=tuple(direct[:MAX_REASONS]),
            data_state=state,
        )

    # M-08. 30분을 넘긴 자료는 등급 산출에서 뺀다. AI 확률과 강우가 여기 해당하고,
    # 위의 직접 안전신호는 이미 지나간 뒤라 영향을 받지 않는다 - 자기신고와 공식
    # 지시는 내부 관측 자료가 아니기 때문이다.
    #
    # 빼도 SAFE 로 내려가지 않는다: expired 는 degraded 를 참으로 만들고, 아래
    # _quality_reasons 가 사유를 채우므로 마지막 분기에서 CAUTION 에 걸린다.
    extra = [] if state.expired else _additional_signals(signals)
    ai_high = (not state.expired) and signals.ai_risk_level is AiRiskLevel.HIGH

    if ai_high:
        ai_reason = Reason(
            "AI_AREA_HIGH",
            "30분 뒤 지역 고수위 위험이 높게 예측됐습니다.",
            Basis.AI_PREDICTION,
        )
        if extra:
            return ServiceRiskResult(
                level=ServiceRiskLevel.DANGER,
                reasons=tuple(([ai_reason] + extra + _quality_reasons(state))[:MAX_REASONS]),
                data_state=state,
            )
        return ServiceRiskResult(
            level=ServiceRiskLevel.CAUTION,
            reasons=tuple(([ai_reason] + _quality_reasons(state))[:MAX_REASONS]),
            data_state=state,
        )

    # AI 가 HIGH 가 아닌데 강우가 기준을 넘은 경우. 복합 위험은 아니지만
    # 이 상태를 '안전'이라고 말하지 않는다 - 같은 신호가 행동 우선순위 9 에서
    # WAIT 을 만든다.
    caution = extra + _quality_reasons(state)
    if caution:
        return ServiceRiskResult(
            level=ServiceRiskLevel.CAUTION,
            reasons=tuple(caution[:MAX_REASONS]),
            data_state=state,
        )

    return ServiceRiskResult(
        level=ServiceRiskLevel.SAFE,
        reasons=(
            Reason(
                "NO_DIRECT_SIGNAL",
                "직접적인 위험 신호가 없고 지역 위험도 낮게 예측됐습니다.",
                Basis.TEAM_RULE,
            ),
        ),
        data_state=state,
    )
