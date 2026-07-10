from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from backend.services import open_transport_registry as registry


def _write_gtfs_zip(path: Path) -> None:
    files = {
        "stops.txt": "stop_id,stop_name,stop_lat,stop_lon\nCJJ,춘천역,37.88456,127.71666\nPUS,부산항,35.1151,129.0403\n",
        "routes.txt": "route_id,route_short_name,route_long_name\nR1,KTX,춘천-부산\n",
        "trips.txt": "route_id,service_id,trip_id,trip_headsign\nR1,WKD,T1,부산항\n",
        "stop_times.txt": "trip_id,arrival_time,departure_time,stop_id,stop_sequence\nT1,08:00:00,08:00:00,CJJ,1\nT1,13:30:00,13:30:00,PUS,2\n",
        "calendar.txt": "service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date\nWKD,1,1,1,1,1,1,1,20260101,20261231\n",
    }
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)


def test_list_route_schedule_options_reads_local_gtfs(tmp_path, monkeypatch) -> None:
    feed_zip = tmp_path / "kr-gtfs.zip"
    _write_gtfs_zip(feed_zip)
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "feeds": [
                    {
                        "id": "kr-test",
                        "country_code": "KR",
                        "label": "KR Test Feed",
                        "provider": "gtfs_schedule",
                        "mode": "rail",
                        "feed_url": str(feed_zip),
                        "timezone": "Asia/Seoul",
                        "website": "https://example.test/kr-gtfs",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(registry, "OPEN_TRANSPORT_REGISTRY_PATH", registry_path)

    options = registry.list_route_schedule_options(
        country_code="KR",
        origin_query="춘천",
        destination_query="부산",
        now=datetime(2026, 7, 7, 7, 0),
    )

    assert len(options) == 1
    first = options[0]
    assert first.provider_id == "kr-test"
    assert first.route_label == "춘천-부산"
    assert first.origin_stop == "춘천역"
    assert first.destination_stop == "부산항"
    assert first.departure_local == "08:00"
    assert first.arrival_local == "13:30"


def test_build_route_schedule_grounding_formats_gtfs_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        registry,
        "list_route_schedule_options",
        lambda **_: [
            registry.TransportScheduleOption(
                provider_id="kr-test",
                provider_label="KR Test Feed",
                route_label="춘천-부산",
                origin_stop="춘천역",
                destination_stop="부산항",
                departure_local="08:00",
                arrival_local="13:30",
                trip_headsign="부산항",
                source_url="https://example.test/kr-gtfs",
            )
        ],
    )

    grounding = registry.build_route_schedule_grounding(
        country_code="KR",
        origin_query="춘천",
        destination_query="부산",
        language="ko",
    )

    assert "KR Test Feed" in grounding
    assert "출발 춘천역 08:00" in grounding
    assert "도착 부산항 13:30" in grounding


def test_load_public_gtfs_jp_auto_feeds_expands_beyond_seed_preferences(monkeypatch) -> None:
    csv_text = """feed_id,prefcode,label,Management,fixed_current_url,license_name
f1,13,[ODPT] 東京都交通局 都営バス,1,https://example.test/toei-bus.zip,CC BY 4.0
f2,13,[ODPT] 台東区コミュニティバス,1,https://example.test/taito.zip,CC BY 4.0
f3,13,[ODPT] 西東京市はなバス,1,https://example.test/nishi.zip,CC BY 4.0
f4,13,[ODPT] 東京都交通局 鉄道関連情報,1,https://example.test/toei-train.zip,CC BY 4.0
f5,13,[ODPT] 東京都町田市 コミュニティバス,1,https://example.test/machida.zip,CC 0
f6,12,[ODPT] 京成トランジットバス,1,https://example.test/keisei.zip,CC BY 4.0
f7,13,[ODPT] 東京都国分寺市地域バスぶんバス,1,https://example.test/kokubunji.zip,CC BY 4.0
"""

    monkeypatch.setattr(
        registry,
        "cached_fetch",
        lambda namespace, key_parts, fetch_fn, **kwargs: csv_text,
    )

    feeds = registry._load_public_gtfs_jp_auto_feeds(max_items=8)

    assert len(feeds) >= 6
    urls = [str(feed.get("resolved_feed_url") or "") for feed in feeds]
    assert "https://example.test/toei-bus.zip" in urls
    assert "https://example.test/taito.zip" in urls
    assert "https://example.test/nishi.zip" in urls
    assert "https://example.test/toei-train.zip" in urls
    assert "https://example.test/keisei.zip" in urls