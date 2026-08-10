# 마른길 통합 데이터

이 폴더는 `C:\2026_Mareungil\datasets`와 `C:\2026_Mareungil\data`에서 실사용 가능한 파일만 역할별로 재구성한 통합 진입점이다.

## 중요

- 기존 두 폴더는 삭제하거나 이동하지 않았다.
- 데이터 파일은 NTFS 하드링크로 연결했다. 추가 디스크 사용량은 거의 없지만, 통합 폴더에서 파일을 수정하면 기존 폴더의 같은 원본도 함께 바뀐다.
- `raw` 파일은 읽기 전용으로 취급하고 절대로 직접 수정하지 않는다.
- 전처리 결과는 추후 `interim` 또는 `processed` 폴더를 만들어 별도로 저장한다.
- 실제 API 인증키는 이 폴더에 저장하지 않는다.

## 구조

```text
data_unified/
├─ raw/
│  ├─ seoul/
│  │  ├─ rainfall/2022/monthly
│  │  ├─ rainfall/stations
│  │  └─ sewer_level/2022/monthly
│  └─ kma/
│     └─ aws
├─ reference/
│  ├─ needs_validation/rainfall_2023_2025
│  ├─ needs_mapping/sewer_level_hourly_gangnam_2023_2025
│  └─ spatial/flood_footprints
├─ pending/
│  └─ kma_ultra_short_forecast/2022
└─ metadata/
   └─ source_manifest.csv
```

## 사용등급

| 위치 | 사용등급 | 용도 |
|---|---|---|
| `raw/seoul/rainfall/2022` | 핵심 | 10분 강우 입력 |
| `raw/seoul/sewer_level/2022` | 핵심·메타데이터 보완 필요 | 예측 입력 및 정답 수위 |
| `raw/kma/aws/minute/2022` | 보조 | 서울시 강우 검증·결측 확인 |
| `raw/kma/aws/hourly/2022` | 참고 | 서울권 광역 강우 비교 |
| `reference/needs_validation/rainfall_2023_2025` | 검증 후 사용 | 다년 확장 후보 |
| `reference/needs_mapping/sewer_level_hourly_gangnam_2023_2025` | 매핑 후 사용 | 다년 수위 확장 후보 |
| `reference/spatial/flood_footprints` | 참고·경로엔진 | 지역위험 검증과 정적 침수정보 |
| `pending/kma_ultra_short_forecast/2022` | 미수집 | 과거 예보 기반 백테스트 |

파일별 원래 위치와 판정은 `metadata/source_manifest.csv`에서 확인한다.

