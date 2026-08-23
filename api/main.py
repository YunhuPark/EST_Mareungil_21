"""통합 API — UI 에 AssessResponse 하나를 제공한다.

    .\\make.ps1 api        # http://127.0.0.1:8000  (문서: /docs)

지금 상태
---------
`decision` 블록은 `classify()`/`decide()`/`apply()`를 실제로 호출해 채운다(P0-5).
`route` 블록도 이제 실제 경로 엔진(`DesignatedPointRouteProvider`)을 거친다(P0-6) —
단, `DS-S7`·`DS-S8`은 시설 만석 서사가 진짜 엔진으로 재현되지 않아 여전히 픽스처
STUB(`FixtureRouteProvider`)을 쓴다. 그래서 `source_kind`도 시나리오별로 갈린다:
`DS-S1`·`DS-S4`·`DS-S6`은 `LIVE_PIPELINE`, `DS-S7`·`DS-S8`은 `FIXTURE`로 남는다.

이 파일이 하는 일은 넷이다.
1. 픽스처를 읽고
2. 사용자가 고른 목적지·프로필을 반영하고
3. RiskSignals 로 변환해 `classify()`/`decide()`로 1차 행동을 정하고,
   그 행동으로 `RouteRequest` 를 만들어 경로 엔진에 넘긴 뒤 `apply()`로
   최종 행동을 정해 decision·route 블록을 채우고
4. **돌려주기 전에 계약을 검증한다.**

4번이 핵심이다. 계약 위반을 UI 가 아니라 여기서 잡아야 다섯 명이 병렬로 만들 때
통합이 덜 깨진다.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from api.fixtures import (
    apply_destination,
    apply_profiles,
    apply_trapped,
    contract_errors,
    load_destinations,
    load_safe_points,
    load_scenarios,
    load_validators,
)
from api.ratelimit import RateLimitMiddleware, TokenBucketLimiter
from services.decision.enums import Profile
from services.pipeline import apply_engine, provider_for

logger = logging.getLogger("mareungil.api")

CONTRACT_VERSION = os.environ.get("MAREUNGIL_CONTRACT_VERSION", "v1")
DEFAULT_SCENARIO = os.environ.get("MAREUNGIL_DEFAULT_SCENARIO", "DS-S1")

#: 배포 환경. `production` 이면 대화형 문서(`/docs`·`/redoc`·`/openapi.json`)를 닫는다.
#: 개발에서는 그대로 열어 둔다 — 이 파일 맨 위가 안내하는 그 문서다.
IS_PRODUCTION = os.environ.get("MAREUNGIL_ENV", "development").strip().lower() == "production"

#: 브라우저에서 이 API 를 부를 수 있는 출처. **기본값은 로컬 개발 주소뿐이다.**
#:
#: 예전에는 `["*"]` 을 박아 두고 바로 옆에 "데모는 로컬 전용"이라고 적어 두었는데,
#: `render.yaml` 로 배포한 순간 그 주석이 사실이 아니게 됐다. 자격증명을 싣지 않으니
#: 훔쳐갈 세션은 없지만, **허용 출처는 코드가 아니라 배포 설정이 정하는 값이다.**
#:
#:     MAREUNGIL_CORS_ORIGINS=https://mareungil.vercel.app
#:     MAREUNGIL_CORS_ORIGIN_REGEX=https://mareungil-.*\.vercel\.app   # 프리뷰 배포
#:
#: 정말 전부 열어야 하면 `MAREUNGIL_CORS_ORIGINS=*` 로 **명시해서** 연다. 기본값에
#: 숨어 있는 것과 배포 설정에 적혀 있는 것은 다른 상태다.
DEFAULT_CORS_ORIGINS = (
    "http://127.0.0.1:5173,http://localhost:5173,"
    "http://127.0.0.1:4173,http://localhost:4173"
)
CORS_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("MAREUNGIL_CORS_ORIGINS", DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
CORS_ORIGIN_REGEX = os.environ.get("MAREUNGIL_CORS_ORIGIN_REGEX") or None

#: 한 IP 가 `MAREUNGIL_RATE_WINDOW_SEC` 초 동안 보낼 수 있는 요청 수. `0` 이면 끈다.
#:
#: 기본값 60회/60초는 **사람이 쓰다가 걸릴 일이 없는 값**으로 잡았다. 화면 하나가
#: 움직일 때 API 를 세 번 부르므로 분당 20번 조작해야 닿는다. 막으려는 것은 사용자가
#: 아니라 초당 수십 번 두드리는 쪽이다.
RATE_LIMIT = int(os.environ.get("MAREUNGIL_RATE_LIMIT", "60"))
RATE_WINDOW_SEC = float(os.environ.get("MAREUNGIL_RATE_WINDOW_SEC", "60"))

#: 앞에 둔 **신뢰하는** 프록시 단수. 0 이면 `X-Forwarded-For` 를 아예 믿지 않는다.
#:
#: Render 처럼 프록시 뒤에 놓을 때만 1 로 준다(`render.yaml`). 틀리게 크게 잡으면
#: 클라이언트가 적어 보낸 값을 믿게 되어 한도를 우회당하고, 프록시 뒤인데 0 으로
#: 두면 모든 요청이 프록시 IP 하나로 뭉쳐 서로의 한도를 갉아먹는다.
TRUSTED_PROXY_HOPS = int(os.environ.get("MAREUNGIL_TRUSTED_PROXY_HOPS", "0"))

app = FastAPI(
    title="마른길 통합 API",
    version="0.1.0",
    description=(
        "2022-08-08 강남 집중호우 재생. **교육·시연용이며 공식 재난안전 판단 도구가 아니다.** "
        "위험·행동 판정은 실제 엔진이 계산하고, 경로는 시나리오에 따라 실제 엔진과 "
        "픽스처로 갈린다. 어느 쪽인지는 응답의 source_kind 필드가 시나리오마다 밝힌다."
    ),
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# --- 미들웨어 -----------------------------------------------------------------
#
# **나중에 add 한 것이 바깥에 선다**(Starlette). 그래서 아래 순서는 이렇게 감싼다:
#
#     security_headers  ->  CORS  ->  RateLimit  ->  앱
#
# 빈도 제한을 CORS 안쪽에 두는 이유가 있다. 429 응답에도 CORS 헤더가 붙어야
# 브라우저가 그것을 "요청이 잦다"로 읽는다. 바깥에 두면 화면에는 정체불명의
# CORS 오류만 뜨고 진짜 이유가 사라진다.

if RATE_LIMIT > 0:
    app.add_middleware(
        RateLimitMiddleware,
        limiter=TokenBucketLimiter(RATE_LIMIT, RATE_WINDOW_SEC),
        trusted_hops=TRUSTED_PROXY_HOPS,
    )

# 프론트(Vite 개발 서버·배포된 웹)에서 직접 호출할 수 있게 열어둔다.
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_origin_regex=CORS_ORIGIN_REGEX,
    allow_methods=["GET"],
    allow_headers=["*"],
)

#: 모든 응답에 붙이는 방어 헤더.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}


@app.middleware("http")
async def security_headers(request: Request, call_next) -> Response:
    """스니핑·클릭재킹·리퍼러 유출을 막는 헤더를 붙인다.

    `/api/*` 에는 CSP 까지 건다 — 이 API 는 JSON 밖에 돌려주지 않으므로 무엇도
    불러올 필요가 없고 프레임에 실릴 이유도 없다. 문서 페이지(`/docs`)에는 걸지
    않는다. Swagger UI 가 CDN 스크립트를 쓰므로 같은 CSP 를 걸면 빈 화면이 된다.
    """
    response = await call_next(request)
    for name, value in SECURITY_HEADERS.items():
        response.headers.setdefault(name, value)
    if request.url.path.startswith("/api/"):
        response.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
    return response


#: 오류 메시지에 사용자 입력을 되비칠 때의 길이 상한.
ECHO_LIMIT = 64


def _echo(value: str) -> str:
    """사용자 입력을 오류 메시지에 넣기 전에 자른다.

    자르지 않으면 5만 자를 보낸 요청이 5만 자를 그대로 돌려받는다 — 서버가 남의
    입력을 증폭해 주는 셈이다. 무엇을 잘못 보냈는지 알려주는 데 64자면 충분하다.
    """
    text = str(value)
    if len(text) <= ECHO_LIMIT:
        return text
    return f"{text[:ECHO_LIMIT]}…(총 {len(text)}자)"


_validators = load_validators()
_scenarios = load_scenarios()
_destinations = load_destinations()
_points = {p["id"]: p for p in _destinations["points"]}
_safe_points = load_safe_points()
#: 손으로 쓴 경로 블록. `DS-S7`·`DS-S8` 만 실제로 쓴다 — 나머지는 경로 엔진이
#: 계산하므로 여기 있어도 무시된다.
_fixture_routes = {sid: body["route"] for sid, body in _scenarios.items()}


@app.get("/api/health")
def health() -> dict:
    """개발 서버가 살아 있는지, 픽스처를 몇 개 읽었는지."""
    return {
        "status": "ok",
        "contract_version": CONTRACT_VERSION,
        "scenarios": sorted(_scenarios),
        "destinations": len(_points),
        "source_kind": "FIXTURE",
    }


#: 계획된 DS 시나리오 전체. 여기서 실제 로드된 것을 빼면 `pending` 이다.
#: 목록을 손으로 두 번 적으면 픽스처를 추가해도 "아직 없음"이 남는다.
PLANNED_SCENARIOS = ["DS-S1", "DS-S2", "DS-S3", "DS-S4", "DS-S5", "DS-S6", "DS-S7", "DS-S8"]


@app.get("/api/scenarios")
def scenarios() -> dict:
    """M-18. 수동 재판단이 고를 수 있는 재생 시각.

    자동 감지·자동 재탐색은 MVP 범위 밖이므로 여기서 시각을 바꾸는 것이
    재판단의 유일한 방법이다. 아직 만들지 않은 시나리오는 `pending` 으로
    구분해 돌려준다 — 없는 것을 있는 척하지 않는다.
    """
    return {
        "scenarios": [
            {
                "id": sid,
                "label": body.get("_scenario", sid),
                "why": body.get("_why_this_moment"),
                "clock_label": body["clock"]["label"],
                "action": body["decision"]["action"],
            }
            for sid, body in sorted(_scenarios.items())
        ],
        "pending": [sid for sid in PLANNED_SCENARIOS if sid not in _scenarios],
    }


@app.get("/api/destinations")
def destinations() -> dict:
    """RT-14. 목적지로 고를 수 있는 지정 지점 목록.

    자유 좌표·자유 텍스트 입력은 제공하지 않는다. 목록 등재가 안전 보장은
    아니며 차단 여부는 재생 시각마다 다시 판정한다(RT-17).
    """
    return {
        "status": _destinations["_status"],
        "scope": _destinations["scope"],
        "points": _destinations["points"],
        "note": "목록에 있다는 사실이 안전을 보장하지 않습니다.",
    }


def _engine(body: dict, profiles: list[str]) -> dict:
    """이 저장소의 데이터로 조립 파이프라인을 부른다.

    **조립 자체는 `services/pipeline` 이 한다.** 여기 남은 것은 "어떤 안전거점
    목록과 어떤 픽스처 경로를 쓰는가" 뿐이다 — 픽스처 생성기가 같은 함수를
    같은 데이터로 부르므로, 생성된 픽스처와 API 응답이 갈라질 수 없다.
    """
    provider = provider_for(body, _safe_points, _fixture_routes)
    return apply_engine(body, profiles, provider)


@app.get("/api/assess")
def assess(
    scenario: str = Query(default=DEFAULT_SCENARIO, description="재생 시나리오 id"),
    destination: str | None = Query(default=None, description="지정 지점 id (RT-14)"),
    profile: list[str] = Query(
        default=[],
        description=(
            "M-37. 고령자·아이동반 프로필. 순서 조정용이며 안전 기준을 완화하지 않는다. "
            "우회 상한 1.15를 통해 경로 후보 순서를 조정하고 route.profile_applied 에 "
            "그 결과를 반영한다. (경사 가중치 1.5는 데이터 부재로 적용 불가)"
        ),
    ),
    trapped: bool = Query(
        default=False,
        description=(
            "M-19. 사용자가 직접 누른 고립 신고. decide() 규칙 1 이며 EMERGENCY 로 간다. "
            "EVACUATE 경로 실패는 여기로 오지 않는다(M-15). 끄는 값을 보내도 픽스처의 "
            "고립 상태를 뒤집지 않는다 — 켜는 방향으로만 동작한다."
        ),
    ),
) -> dict:
    """UI 가 받는 단일 응답.

    돌려주기 전에 `AssessResponse` + `RiskAssessment` + `SafeRoute` 를 모두 검증한다.
    위반이 있으면 500 으로 떨어뜨린다 — 계약을 어긴 응답을 화면까지 보내지 않는다.
    """
    body = _scenarios.get(scenario)
    if body is None:
        raise HTTPException(
            404,
            f"시나리오 {_echo(scenario)} 가 없다. 사용 가능: {sorted(_scenarios)}",
        )

    if destination is not None:
        point = _points.get(destination)
        if point is None:
            # RT-14/RT-15. 목록 밖 지점은 애초에 받지 않는다.
            raise HTTPException(
                400,
                f"지정 지점 목록에 없는 목적지 {_echo(destination)}. 사용 가능: {sorted(_points)}",
            )
        body = apply_destination(body, point)

    if profile:
        # X1 / C-14. WHEELCHAIR·WITH_PET 은 계약 enum 밖이다. 여기서 막지 않으면
        # 계약 검증에서 500 이 되는데, 그건 사용자 입력 오류를 서버 오류로 보고하는 것이다.
        unknown = [p for p in profile if p not in {m.value for m in Profile}]
        if unknown:
            raise HTTPException(
                400,
                f"MVP 가 지원하지 않는 프로필 {[_echo(p) for p in unknown[:5]]}. "
                f"사용 가능: {sorted(m.value for m in Profile)}",
            )
        # 계약은 프로필을 집합으로 본다(`uniqueItems`). 중복을 그대로 흘리면 아래
        # 계약 검증이 500 을 내는데, 그것이야말로 이 블록이 막으려던 상황이다 —
        # `?profile=ELDERLY&profile=ELDERLY` 한 번이면 사용자 입력 오류가 서버
        # 오류로 보고된다. 고른 순서는 유지한 채 중복만 걷어낸다.
        profile = list(dict.fromkeys(profile))
        body = apply_profiles(body, profile)

    if trapped:
        # 켜는 방향으로만 적용한다. `trapped=false` 로 픽스처의 고립 상태를 끄면
        # `DS-S4` 가 EMERGENCY 를 잃는데, 그건 사용자가 취소한 것이 아니라 기본값이
        # 덮어쓴 것이다. 신고는 사용자만 만들고, 아무도 대신 지우지 않는다.
        body = apply_trapped(body)

    body = _engine(body, profile)

    violations = contract_errors(_validators, body)
    if violations:
        # 계약 위반은 **서버 잘못이다.** 무엇이 어긋났는지는 로그에 남기고 클라이언트
        # 에는 스키마 경로를 주지 않는다 — 내부 구조를 그대로 읽어주는 응답은 정찰에
        # 쓰인다. 개발 중에는 서버 콘솔에서 같은 내용을 그대로 본다.
        logger.error(
            "계약 위반 (scenario=%s, destination=%s, profiles=%s): %s",
            scenario, destination, profile, violations[:10],
        )
        raise HTTPException(500, "응답이 내부 계약을 어겼다. 서버 로그를 확인하라.")

    return body
