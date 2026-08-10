from __future__ import annotations

import argparse
import json
import math
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests


ROOT = Path(r"C:\2026_Mareungil")
KEY_PATHS = [
    ROOT / ".secrets" / "seoul_openapi_key.txt",
    ROOT / "secrets" / "seoul_openapi_key.txt",
]
SEWER_2022_DIR = ROOT / "data_unified" / "raw" / "seoul" / "sewer_level" / "2022" / "monthly"
RAW_API_DIR = ROOT / "data_unified" / "raw" / "seoul" / "sewer_level" / "2022" / "api_location"
METADATA_DIR = ROOT / "data_unified" / "metadata" / "sewer_sensors"
PROCESSED_DIR = ROOT / "data_unified" / "processed" / "sewer_risk_modeling_2022"

DISTRICTS = {"22": "서초", "23": "강남"}
EVENT_HOUR = "2022080821"
SNAPSHOT_HOURS = [f"2022{month:02d}1512" for month in range(1, 13)] + [
    EVENT_HOUR,
    "2022081812",
    "2022082112",
]

SEOUL_API_TEMPLATE = (
    "http://openAPI.seoul.go.kr:8088/{key}/json/DrainpipeMonitoringInfo/"
    "{start}/{end}/{district}/{hour}/{hour}"
)
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_USER_AGENT = "MareungilRiskResearch/1.0 (one-time academic sensor address geocoding)"
SEOUL_BOUNDS = {"lat_min": 37.40, "lat_max": 37.75, "lon_min": 126.75, "lon_max": 127.25}


def ensure_dirs() -> None:
    for path in (RAW_API_DIR, METADATA_DIR, PROCESSED_DIR):
        path.mkdir(parents=True, exist_ok=True)


def read_api_key() -> str:
    for path in KEY_PATHS:
        if path.exists():
            key = path.read_text(encoding="utf-8-sig").strip()
            if len(key) >= 10:
                return key
    raise FileNotFoundError(
        "서울 Open API 키 파일을 찾지 못했습니다: " + ", ".join(str(p) for p in KEY_PATHS)
    )


def atomic_json_dump(data: Any, path: Path) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def request_json(session: requests.Session, url: str, retries: int = 4) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=45)
            response.raise_for_status()
            return response.json()
        except Exception as exc:  # network/API retry boundary
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("서울 Open API 호출 실패") from last_error


def extract_api_block(payload: dict[str, Any]) -> dict[str, Any]:
    block = payload.get("DrainpipeMonitoringInfo")
    if not isinstance(block, dict):
        result = payload.get("RESULT", {})
        raise RuntimeError(f"API 응답 형식 오류: {result.get('CODE')} {result.get('MESSAGE')}")
    result = block.get("RESULT", {})
    if result.get("CODE") != "INFO-000":
        raise RuntimeError(f"API 오류: {result.get('CODE')} {result.get('MESSAGE')}")
    return block


def collect_locations() -> None:
    ensure_dirs()
    key = read_api_key()
    session = requests.Session()
    session.headers.update({"User-Agent": NOMINATIM_USER_AGENT})
    summary_rows: list[dict[str, Any]] = []
    snapshot_rows: list[dict[str, Any]] = []

    for district_code, district_name in DISTRICTS.items():
        for hour in sorted(set(SNAPSHOT_HOURS)):
            first_url = SEOUL_API_TEMPLATE.format(
                key=key, start=1, end=1000, district=district_code, hour=hour
            )
            payload = request_json(session, first_url)
            block = extract_api_block(payload)
            total = int(block.get("list_total_count", 0))
            page_count = max(1, math.ceil(total / 1000))
            all_rows: list[dict[str, Any]] = []

            for page_index in range(page_count):
                start = page_index * 1000 + 1
                end = min((page_index + 1) * 1000, total)
                if page_index == 0:
                    page_payload = payload
                    page_block = block
                else:
                    page_url = SEOUL_API_TEMPLATE.format(
                        key=key, start=start, end=end, district=district_code, hour=hour
                    )
                    page_payload = request_json(session, page_url)
                    page_block = extract_api_block(page_payload)
                    time.sleep(0.15)

                raw_path = RAW_API_DIR / f"district_{district_code}_{hour}_{start:06d}_{end:06d}.json"
                atomic_json_dump(page_payload, raw_path)
                rows = page_block.get("row") or []
                all_rows.extend(rows)

            grouped: dict[tuple[str, str], dict[str, Any]] = {}
            for row in all_rows:
                unq_no = str(row.get("UNQ_NO", "")).strip()
                location = str(row.get("PSTN_INFO", "") or "").strip()
                key_pair = (unq_no, location)
                item = grouped.setdefault(
                    key_pair,
                    {
                        "query_hour": hour,
                        "unq_no": unq_no,
                        "se_cd": str(row.get("SE_CD", district_code)).strip(),
                        "se_nm": str(row.get("SE_NM", district_name)).strip(),
                        "pstn_info_raw": location,
                        "row_count": 0,
                        "measurement_min": None,
                        "measurement_max": None,
                    },
                )
                item["row_count"] += 1
                measured_at = str(row.get("MSRMT_YMD", "")).strip()
                if measured_at:
                    item["measurement_min"] = min(
                        measured_at, item["measurement_min"] or measured_at
                    )
                    item["measurement_max"] = max(
                        measured_at, item["measurement_max"] or measured_at
                    )

            snapshot_rows.extend(grouped.values())
            summary_rows.append(
                {
                    "query_hour": hour,
                    "se_cd": district_code,
                    "se_nm": district_name,
                    "api_total_rows": total,
                    "downloaded_rows": len(all_rows),
                    "unique_sensors": len({r.get("UNQ_NO") for r in all_rows}),
                    "unique_sensor_location_pairs": len(grouped),
                    "blank_location_pairs": sum(1 for _, location in grouped if not location),
                }
            )
            print(
                f"[collect] {hour} {district_name}: rows={len(all_rows):,}, "
                f"sensors={summary_rows[-1]['unique_sensors']}"
            )

    snapshots = pd.DataFrame(snapshot_rows)
    snapshots.to_csv(
        METADATA_DIR / "sensor_location_api_snapshots.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(summary_rows).to_csv(
        METADATA_DIR / "sensor_location_api_collection_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    history_rows: list[dict[str, Any]] = []
    for (unq_no, location), group in snapshots.groupby(["unq_no", "pstn_info_raw"], dropna=False):
        hours = sorted(group["query_hour"].astype(str).unique())
        history_rows.append(
            {
                "unq_no": unq_no,
                "se_cd": str(group["se_cd"].iloc[0]),
                "se_nm": str(group["se_nm"].iloc[0]),
                "pstn_info_raw": location,
                "first_sampled_hour": hours[0],
                "last_sampled_hour": hours[-1],
                "sampled_hour_count": len(hours),
                "api_row_count": int(group["row_count"].sum()),
                "includes_event_hour": EVENT_HOUR in hours,
            }
        )
    history = pd.DataFrame(history_rows).sort_values(["unq_no", "first_sampled_hour"])
    history.to_csv(METADATA_DIR / "sensor_location_history.csv", index=False, encoding="utf-8-sig")

    selected_rows: list[dict[str, Any]] = []
    for unq_no, group in history.groupby("unq_no"):
        candidates = group.copy()
        event_candidates = candidates[candidates["includes_event_hour"] & candidates["pstn_info_raw"].ne("")]
        if not event_candidates.empty:
            chosen = event_candidates.sort_values(
                ["sampled_hour_count", "api_row_count"], ascending=False
            ).iloc[0]
            rule = "EVENT_HOUR_2022080821"
        else:
            nonblank = candidates[candidates["pstn_info_raw"].ne("")]
            pool = nonblank if not nonblank.empty else candidates
            chosen = pool.sort_values(["sampled_hour_count", "api_row_count"], ascending=False).iloc[0]
            rule = "MOST_OBSERVED_2022_SNAPSHOTS"
        record = chosen.to_dict()
        record["selection_rule"] = rule
        record["location_variant_count"] = int(candidates["pstn_info_raw"].nunique(dropna=False))
        record["historical_validity_confirmed"] = False
        selected_rows.append(record)

    selected = pd.DataFrame(selected_rows).sort_values("unq_no")
    selected.to_csv(
        METADATA_DIR / "sensor_metadata_2022_address.csv", index=False, encoding="utf-8-sig"
    )
    print(f"[collect] selected sensor metadata: {len(selected)} sensors")


def normalize_address(raw: str, district_name: str) -> list[str]:
    text = re.sub(r"\s+", " ", str(raw or "").replace("\n", " ")).strip()
    if not text:
        return []
    # Normalize Korean road names before extracting a road-number candidate.
    # Examples: "광평로 20길" -> "광평로20길", "테헤란로435" -> "테헤란로 435".
    text = re.sub(r"(대로|로)\s+(\d+)길", r"\1\2길", text)
    text = re.sub(r"(대로|로|길)(\d+(?:-\d+)?)(?!길)", r"\1 \2", text)
    district_full = f"{district_name}구" if district_name else ""
    if text.startswith("서울"):
        pass
    elif district_full and text.startswith(district_full):
        text = f"서울특별시 {text}"
    elif district_full:
        text = f"서울특별시 {district_full} {text}"
    else:
        text = f"서울특별시 {text}"
    no_parentheses = re.sub(r"\([^)]*\)", " ", text)
    no_parentheses = re.sub(r"\s+", " ", no_parentheses).strip()

    candidates: list[str] = [no_parentheses, text]
    landmark_matches = re.findall(
        r"([가-힣0-9]+(?:본동)?\s*(?:주민센터|병원|아파트|빌딩))", no_parentheses
    )
    for landmark in landmark_matches:
        candidates.insert(0, f"서울특별시 {district_full} {landmark}".strip())
    road_match = re.search(
        r"(서울특별시\s+)?(강남구|서초구)\s+(.+?(?:대로|로|길)\s*\d+(?:-\d+)?)",
        no_parentheses,
    )
    if road_match:
        road_with_number = road_match.group(3)
        candidates.insert(0, f"서울특별시 {road_match.group(2)} {road_with_number}")
        road_name_only = re.sub(r"\s*\d+(?:-\d+)?$", "", road_with_number).strip()
        candidates.append(f"서울특별시 {road_match.group(2)} {road_name_only}")
    district_prefixed = []
    for candidate in candidates:
        if district_name and district_name not in candidate:
            candidate = f"서울특별시 {district_name}구 {candidate}"
        # Nominatim's Korean address parser performs materially better without
        # an appended country phrase. countrycodes=kr already restricts results.
        district_prefixed.append(candidate)
    return list(dict.fromkeys(district_prefixed))


def in_seoul(lat: float, lon: float) -> bool:
    return (
        SEOUL_BOUNDS["lat_min"] <= lat <= SEOUL_BOUNDS["lat_max"]
        and SEOUL_BOUNDS["lon_min"] <= lon <= SEOUL_BOUNDS["lon_max"]
    )


def district_matches(display_name: str, district_name: str) -> bool:
    aliases = {
        "강남": ["강남구", "Gangnam-gu", "Gangnam"],
        "서초": ["서초구", "Seocho-gu", "Seocho"],
    }
    return any(alias.lower() in display_name.lower() for alias in aliases.get(district_name, []))


def geocode_locations() -> None:
    ensure_dirs()
    source_path = METADATA_DIR / "sensor_metadata_2022_address.csv"
    if not source_path.exists():
        raise FileNotFoundError("먼저 collect 단계를 실행해야 합니다.")
    source = pd.read_csv(source_path, dtype=str, encoding="utf-8-sig").fillna("")
    cache_path = METADATA_DIR / "nominatim_geocode_cache.json"
    cache: dict[str, Any] = (
        json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    )
    session = requests.Session()
    session.headers.update({"User-Agent": NOMINATIM_USER_AGENT})

    output_rows: list[dict[str, Any]] = []
    for index, row in source.iterrows():
        district_name = str(row.get("se_nm", ""))
        raw = str(row.get("pstn_info_raw", ""))
        candidates = normalize_address(raw, district_name)
        selected_result: dict[str, Any] | None = None
        selected_query = ""

        for query in candidates:
            if query in cache:
                results = cache[query]
            else:
                response = session.get(
                    NOMINATIM_URL,
                    params={
                        "q": query,
                        "format": "jsonv2",
                        "addressdetails": 1,
                        "limit": 3,
                        "countrycodes": "kr",
                        "viewbox": "126.75,37.75,127.25,37.40",
                        "bounded": 1,
                        "accept-language": "ko,en",
                    },
                    timeout=45,
                )
                response.raise_for_status()
                results = response.json()
                cache[query] = results
                atomic_json_dump(cache, cache_path)
                time.sleep(1.1)

            for result in results:
                lat = float(result["lat"])
                lon = float(result["lon"])
                if in_seoul(lat, lon) and district_matches(result.get("display_name", ""), district_name):
                    selected_result = result
                    selected_query = query
                    break
            if selected_result:
                break

        record = row.to_dict()
        record["normalized_address"] = candidates[0] if candidates else ""
        record["geocode_query"] = selected_query
        record["geocode_provider"] = "OpenStreetMap Nominatim"
        record["coordinate_crs"] = "EPSG:4326"
        if selected_result:
            lat = float(selected_result["lat"])
            lon = float(selected_result["lon"])
            address_details = selected_result.get("address", {})
            has_house_number = bool(address_details.get("house_number"))
            result_type = str(selected_result.get("type", ""))
            road_number_requested = bool(re.search(r"(?:대로|로|길)\s*\d", selected_query))
            is_landmark_query = bool(
                re.search(r"(?:주민센터|병원|아파트|빌딩|학교|주유소)", selected_query)
            )
            if is_landmark_query:
                quality = "LANDMARK_MATCH_MANUAL_REVIEW"
            elif not road_number_requested:
                quality = "ROAD_NAME_ONLY_APPROX"
            elif has_house_number:
                quality = "EXACT_ADDRESS_CANDIDATE"
            elif result_type in {"road", "residential", "building", "house"}:
                quality = "ROAD_MATCH"
            else:
                quality = "LANDMARK_MATCH_MANUAL_REVIEW"
            record.update(
                {
                    "lat": lat,
                    "lon": lon,
                    "geocode_quality": quality,
                    "geocode_display_name": selected_result.get("display_name", ""),
                    "geocode_osm_type": selected_result.get("osm_type", ""),
                    "geocode_osm_id": selected_result.get("osm_id", ""),
                }
            )
        else:
            record.update(
                {
                    "lat": "",
                    "lon": "",
                    "geocode_quality": "UNMATCHED",
                    "geocode_display_name": "",
                    "geocode_osm_type": "",
                    "geocode_osm_id": "",
                }
            )
        output_rows.append(record)
        print(
            f"[geocode] {index + 1}/{len(source)} {row['unq_no']}: "
            f"{record['geocode_quality']}"
        )

    output = pd.DataFrame(output_rows)
    output.to_csv(
        METADATA_DIR / "sensor_metadata_2022_geocoded.csv", index=False, encoding="utf-8-sig"
    )
    quality_summary = (
        output.groupby(["se_nm", "geocode_quality"], dropna=False)
        .size()
        .reset_index(name="sensor_count")
    )
    quality_summary.to_csv(
        METADATA_DIR / "sensor_geocode_quality_summary.csv", index=False, encoding="utf-8-sig"
    )
    print("[geocode] OpenStreetMap attribution: OpenStreetMap contributors, ODbL 1.0")


def join_coverage_and_event() -> None:
    ensure_dirs()
    metadata_path = METADATA_DIR / "sensor_metadata_2022_geocoded.csv"
    if not metadata_path.exists():
        fallback = METADATA_DIR / "sensor_metadata_2022_address.csv"
        if not fallback.exists():
            raise FileNotFoundError("먼저 collect 단계를 실행해야 합니다.")
        metadata_path = fallback
    metadata = pd.read_csv(metadata_path, dtype=str, encoding="utf-8-sig").fillna("")
    metadata["구분코드"] = metadata["se_cd"].astype(str).str.zfill(2)

    coverage_path = METADATA_DIR / "sensor_location_join_coverage_2022.csv"
    if coverage_path.exists():
        coverage_df = pd.read_csv(coverage_path, dtype=str, encoding="utf-8-sig")[
            ["month", "unq_no", "se_cd", "se_nm", "measurement_rows"]
        ]
        coverage_df["measurement_rows"] = pd.to_numeric(
            coverage_df["measurement_rows"], errors="raise"
        ).astype("int64")
        print("[join] reused cached annual coverage counts")
    else:
        coverage: dict[tuple[str, str, str], int] = defaultdict(int)
        monthly_paths = sorted(SEWER_2022_DIR.glob("*.csv"))
        for path in monthly_paths:
            month = path.stem[-6:]
            for chunk in pd.read_csv(
                path,
                encoding="cp949",
                dtype=str,
                usecols=["고유번호", "구분코드", "구분명"],
                chunksize=750_000,
            ):
                chunk["구분코드"] = chunk["구분코드"].astype(str).str.zfill(2)
                chunk = chunk[chunk["구분코드"].isin(DISTRICTS)]
                counts = chunk.groupby(["고유번호", "구분코드", "구분명"]).size()
                for key, count in counts.items():
                    coverage[(month, *key)] += int(count)
            print(f"[join] coverage scanned: {path.name}")

        coverage_df = pd.DataFrame(
            [
                {
                    "month": key[0],
                    "unq_no": key[1],
                    "se_cd": key[2],
                    "se_nm": key[3],
                    "measurement_rows": count,
                }
                for key, count in coverage.items()
            ]
        )
    coverage_df = coverage_df.merge(
        metadata[["unq_no", "pstn_info_raw", "lat", "lon", "geocode_quality"]]
        if "lat" in metadata.columns
        else metadata[["unq_no", "pstn_info_raw"]],
        on="unq_no",
        how="left",
        validate="many_to_one",
    )
    coverage_df["metadata_matched"] = coverage_df["pstn_info_raw"].fillna("").ne("")
    coverage_df.to_csv(coverage_path, index=False, encoding="utf-8-sig")

    august_path = SEWER_2022_DIR / "하수관로_수위_현황_202208.csv"
    event_chunks: list[pd.DataFrame] = []
    event_start = pd.Timestamp("2022-08-07 00:00:00")
    event_end = pd.Timestamp("2022-08-12 00:00:00")
    for chunk in pd.read_csv(
        august_path,
        encoding="cp949",
        dtype={"고유번호": str, "구분코드": str, "구분명": str, "통신상태": str},
        chunksize=600_000,
    ):
        chunk["구분코드"] = chunk["구분코드"].astype(str).str.zfill(2)
        chunk = chunk[chunk["구분코드"].isin(DISTRICTS)]
        chunk["측정일자"] = pd.to_datetime(chunk["측정일자"], errors="coerce")
        chunk = chunk[(chunk["측정일자"] >= event_start) & (chunk["측정일자"] < event_end)]
        if not chunk.empty:
            event_chunks.append(chunk)

    event = pd.concat(event_chunks, ignore_index=True)
    event["측정수위"] = pd.to_numeric(event["측정수위"], errors="coerce")
    event = event.merge(
        metadata.drop(columns=["구분코드"], errors="ignore"),
        left_on="고유번호",
        right_on="unq_no",
        how="left",
        validate="many_to_one",
    )
    event["location_matched"] = event["pstn_info_raw"].fillna("").ne("")
    if "lat" in event.columns:
        event["coordinate_matched"] = event["lat"].fillna("").astype(str).str.strip().ne("")
    else:
        event["coordinate_matched"] = False
    event.to_parquet(PROCESSED_DIR / "sewer_level_event_20220807_11_with_location.parquet", index=False)

    event["time_10m"] = event["측정일자"].dt.floor("10min")
    event["communication_good"] = event["통신상태"].eq("통신양호").astype(float)
    ten_minute = (
        event.groupby(["고유번호", "구분코드", "구분명", "time_10m"], as_index=False)
        .agg(
            level_last=("측정수위", "last"),
            level_mean=("측정수위", "mean"),
            level_max=("측정수위", "max"),
            level_min=("측정수위", "min"),
            sample_count=("측정수위", "count"),
            communication_good_rate=("communication_good", "mean"),
        )
    )
    metadata_columns = [
        column
        for column in [
            "unq_no",
            "pstn_info_raw",
            "normalized_address",
            "lat",
            "lon",
            "geocode_quality",
            "selection_rule",
            "location_variant_count",
            "historical_validity_confirmed",
        ]
        if column in metadata.columns
    ]
    ten_minute = ten_minute.merge(
        metadata[metadata_columns],
        left_on="고유번호",
        right_on="unq_no",
        how="left",
        validate="many_to_one",
    )
    ten_minute.to_parquet(
        PROCESSED_DIR / "sewer_level_10min_event_20220807_11_with_location.parquet",
        index=False,
    )
    ten_minute.to_csv(
        PROCESSED_DIR / "sewer_level_10min_event_20220807_11_with_location.csv",
        index=False,
        encoding="utf-8-sig",
    )

    join_summary = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "metadata_sensor_count": int(metadata["unq_no"].nunique()),
        "annual_gangnam_seocho_sensor_count": int(coverage_df["unq_no"].nunique()),
        "annual_metadata_matched_sensor_count": int(
            coverage_df.loc[coverage_df["metadata_matched"], "unq_no"].nunique()
        ),
        "event_measurement_rows": int(len(event)),
        "event_sensor_count": int(event["고유번호"].nunique()),
        "event_location_matched_rows": int(event["location_matched"].sum()),
        "event_location_match_rate": float(event["location_matched"].mean()),
        "event_coordinate_matched_rows": int(event["coordinate_matched"].sum()),
        "event_coordinate_match_rate": float(event["coordinate_matched"].mean()),
        "event_10min_rows": int(len(ten_minute)),
        "level_unit": "UNCONFIRMED",
        "physical_fill_ratio_available": False,
    }
    atomic_json_dump(join_summary, METADATA_DIR / "sensor_location_join_summary.json")
    print(json.dumps(join_summary, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["collect", "geocode", "join", "all"])
    args = parser.parse_args()
    if args.command in {"collect", "all"}:
        collect_locations()
    if args.command in {"geocode", "all"}:
        geocode_locations()
    if args.command in {"join", "all"}:
        join_coverage_and_event()


if __name__ == "__main__":
    main()
