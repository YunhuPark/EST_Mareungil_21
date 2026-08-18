/**
 * 맞춤안내 탭 — 시안 첫 화면.
 *
 * "지금 위험한가"와 "지금 무엇을 해야 하는가"를 한 번에 보여주는 자리다.
 * 히어로(위험 등급) → 행동 카드 → 이유 → 지도 → 자료 시각 순서이며,
 * 이 순서는 설계서 12장 그대로다.
 *
 * 히어로의 큰 글자는 **위험 등급**(`service_risk_level`)이고 행동 카드의
 * 제목은 **행동**(`action`)이다. 둘은 다른 축이라 1:1 로 잇지 않는다(C-23) —
 * 같은 DANGER 라도 실내면 대기, 실외면 대피다.
 */

import { ActionCard } from '../components/ActionCard';
import { DataTimes } from '../components/DataTimes';
import { MapPanel } from '../components/MapPanel';
import { ReasonList } from '../components/ReasonList';
import { RISK_LABEL, RISK_MARK } from '../contracts/enums';
import { AlertCircleIcon, AlertTriangleIcon, CheckCircleIcon } from '../components/icons';
import type { AssessResponse, DestinationList, ServiceRiskLevel } from '../contracts/types';

const RISK_ICON = {
  SAFE: CheckCircleIcon,
  CAUTION: AlertCircleIcon,
  DANGER: AlertTriangleIcon,
  SEVERE: AlertTriangleIcon,
} as const;

interface Props {
  data: AssessResponse;
  scope: DestinationList['scope'] | null;
}

export function GuideView({ data, scope }: Props) {
  const { decision, clock, location } = data;
  const risk: ServiceRiskLevel = decision.service_risk_level;
  const Icon = RISK_ICON[risk];

  return (
    <div className="view">
      <section className={`hero ${risk === 'SAFE' ? 'hero--safe' : ''}`} aria-label="위험 등급">
        <span className={`hero__icon tone--${risk.toLowerCase()}`}>
          <Icon size={56} />
        </span>

        {/*
          '위험 등급' 이라는 말은 상단 상태 줄이 갖는다. 여기서 한 번 더 적으면
          같은 문구가 화면에 둘이 되고, 탭을 옮겼을 때 어느 쪽이 남는 표시인지
          흐려진다. 히어로는 등급 값만 크게 말한다.
        */}
        <p className={`hero__risk tone--${risk.toLowerCase()}`}>
          <span className="hero__mark" aria-hidden="true">
            {RISK_MARK[risk]}
          </span>
          {RISK_LABEL[risk]}
        </p>

        <p className="hero__where">
          {location.label} · {clock.label}
        </p>
      </section>

      {/* 지금 보고 있는 값이 모델이 방금 계산한 것인지 고정 데이터인지. */}
      {data.source_kind === 'LIVE_PIPELINE' ? (
        <p className="badge badge--live">LIVE</p>
      ) : (
        <p className="badge badge--stub">
          {data.source_kind ?? 'FIXTURE'} — 재현 가능한 시연·검증용 고정 데이터를 사용하고
          있습니다.
        </p>
      )}

      <ActionCard
        action={decision.action}
        primaryAction={decision.primary_action}
        postprocessApplied={decision.route_postprocess_applied}
        nextCheckAt={decision.next_check_at}
      />

      <ReasonList reasons={decision.reasons} />

      {/* 지도가 실패해도 위의 위험·행동·이유는 그대로 남는다(설계서 8.5.3). */}
      <MapPanel data={data} scope={scope} />

      <DataTimes clock={clock} />

      {!location.in_service_area && <p className="badge badge--warn">서비스 범위 밖입니다</p>}
    </div>
  );
}
