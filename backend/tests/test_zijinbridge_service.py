from datetime import datetime

import pytest
from fastapi import HTTPException

from app.modules.zijinbridge.schema import HistoryQueryIn, SqlQueryIn
from app.modules.zijinbridge.service import ZijinBridgeService


@pytest.mark.asyncio
async def test_private_base_url_is_allowed(monkeypatch):
    monkeypatch.setattr(ZijinBridgeService, "ALLOW_PUBLIC_HOSTS", False)
    assert await ZijinBridgeService.normalize_base_url("http://127.0.0.1:8000/") == "http://127.0.0.1:8000"


@pytest.mark.asyncio
async def test_public_base_url_is_rejected_by_default(monkeypatch):
    monkeypatch.setattr(ZijinBridgeService, "ALLOW_PUBLIC_HOSTS", False)
    with pytest.raises(HTTPException) as exc:
        await ZijinBridgeService.normalize_base_url("http://8.8.8.8:8000")
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_history_times_are_chunked_by_points_and_times(monkeypatch):
    calls: list[dict] = []

    async def fake_request(cls, base_url, method, path, *, token=None, params=None, json_body=None, check_code=True):
        calls.append(dict(params or {}))
        names = (params or {})["names"].split(",")
        times = (params or {})["times"].split(",")
        return {
            "code": 0,
            "items": [
                {
                    "name": name,
                    "vals": [{"time": t, "val": f"{name}@{t}"} for t in times],
                }
                for name in names
            ],
        }

    monkeypatch.setattr(ZijinBridgeService, "request", classmethod(fake_request))
    payload = HistoryQueryIn(
        base_url="http://127.0.0.1:8000",
        mode="times",
        names=["A1.PV", "A2.PV", "A3.PV"],
        times=[
            "2026-09-08T10:00:00.000",
            "2026-09-08T10:00:01.000",
            "2026-09-08T10:00:02.000",
            "2026-09-08T10:00:03.000",
            "2026-09-08T10:00:04.000",
        ],
        names_per_request=2,
        samples_per_request=2,
    )

    result = await ZijinBridgeService.history(payload, "token")
    assert len(calls) == 6
    assert result["meta"]["upstream_requests"] == 6
    assert [len(item["vals"]) for item in result["items"]] == [5, 5, 5]
    assert calls[0]["names"] == "A1.PV,A2.PV"
    assert calls[0]["times"] == "2026-09-08T10:00:00.000,2026-09-08T10:00:01.000"


def test_history_range_is_split_into_safe_windows(monkeypatch):
    monkeypatch.setattr(ZijinBridgeService, "MAX_QUERY_CELLS", 2_000_000)
    payload = HistoryQueryIn(
        base_url="http://127.0.0.1:8000",
        mode="range",
        names=["A1.PV"],
        start_time="2026-09-08T10:00:00.000",
        end_time="2026-09-08T10:00:10.000",
        interval=1000,
        samples_per_request=3,
    )

    windows = ZijinBridgeService._range_windows(payload)
    assert len(windows) == 4
    assert datetime.fromisoformat(windows[0][0]) == datetime.fromisoformat("2026-09-08T10:00:00.000")
    assert datetime.fromisoformat(windows[-1][1]) == datetime.fromisoformat("2026-09-08T10:00:10.000")


@pytest.mark.asyncio
async def test_sql_console_rejects_write_statement_in_read_only_mode(monkeypatch):
    called = False

    async def fake_request(cls, *args, **kwargs):
        nonlocal called
        called = True
        return {"code": 0}

    monkeypatch.setattr(ZijinBridgeService, "request", classmethod(fake_request))
    payload = SqlQueryIn(
        base_url="http://127.0.0.1:8000",
        query="delete from realdata where name = 'A1'",
        read_only=True,
    )

    with pytest.raises(HTTPException) as exc:
        await ZijinBridgeService.sql(payload, None)
    assert exc.value.status_code == 403
    assert called is False


def test_history_csv_preserves_valueonly_time_mapping():
    payload = HistoryQueryIn(
        base_url="http://127.0.0.1:8000",
        mode="range",
        names=["A1.PV"],
        start_time="2026-09-08T10:00:00.000",
        end_time="2026-09-08T10:00:03.000",
        interval=1000,
        value_only=True,
    )
    content = ZijinBridgeService.history_csv(
        payload,
        {"items": [{"name": "A1.PV", "vals": [10, 11, 12]}]},
    ).decode("utf-8-sig")

    assert "A1.PV,2026-09-08T10:00:00.000,10" in content
    assert "A1.PV,2026-09-08T10:00:02.000,12" in content


def test_csv_export_neutralizes_spreadsheet_formula_strings():
    payload = HistoryQueryIn(
        base_url="http://127.0.0.1:8000",
        mode="times",
        names=["A1.DESC"],
        times=["2026-09-08T10:00:00.000"],
    )
    content = ZijinBridgeService.history_csv(
        payload,
        {"items": [{"name": "A1.DESC", "vals": [{"time": "2026-09-08T10:00:00.000", "val": "=1+1"}]}]},
    ).decode("utf-8-sig")
    assert "'=1+1" in content
