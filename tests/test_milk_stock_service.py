import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from milk_stock_service import DEFAULT_CSV, load_milk_rows, make_handler

HEADER = (
    "store_id,store_name,store_open,component_id,component_name,component_type,"
    "quantity_on_hand,reserved_quantity,last_updated_at\n"
)


def write_csv(tmp_path, *rows):
    path = tmp_path / "snapshot.csv"
    path.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return path


def oat_row(store_id, on_hand, reserved, store_open="true"):
    return (
        f"{store_id},Store {store_id},{store_open},oat_milk,Oatmilk,drink_base,"
        f"{on_hand},{reserved},2025-03-07T06:00:00-08:00"
    )


# --- load_milk_rows against the real snapshot ---------------------------------

def test_snapshot_oat_milk_sold_out_status():
    oat = {r["store_id"]: r for r in load_milk_rows(DEFAULT_CSV) if r["component_id"] == "oat_milk"}

    assert set(oat) == {"10482", "11307", "09815"}

    assert oat["10482"]["available_quantity"] == 0
    assert oat["10482"]["sold_out"] is True

    # 2 on hand, 1 reserved -> 1 available, not sold out
    assert oat["11307"]["available_quantity"] == 1
    assert oat["11307"]["sold_out"] is False

    assert oat["09815"]["available_quantity"] == 72
    assert oat["09815"]["sold_out"] is False
    assert oat["09815"]["store_open"] is False


def test_only_milk_components_are_returned():
    rows = load_milk_rows(DEFAULT_CSV)
    assert {r["component_id"] for r in rows} == {"oat_milk", "almond_milk", "two_pct_milk"}
    assert len(rows) == 9  # 3 milks x 3 stores


def test_store_id_keeps_leading_zero():
    ids = {r["store_id"] for r in load_milk_rows(DEFAULT_CSV)}
    assert "09815" in ids


# --- sold-out calculation edge cases -------------------------------------------

@pytest.mark.parametrize(
    "on_hand, reserved, available, sold_out",
    [
        (0, 0, 0, True),    # nothing on hand
        (3, 3, 0, True),    # everything reserved
        (1, 2, -1, True),   # over-reserved
        (2, 1, 1, False),   # one left
        (10, 0, 10, False),
    ],
)
def test_sold_out_calculation(tmp_path, on_hand, reserved, available, sold_out):
    path = write_csv(tmp_path, oat_row("1", on_hand, reserved))
    [row] = load_milk_rows(path)
    assert row["available_quantity"] == available
    assert row["sold_out"] is sold_out


# --- HTTP service ----------------------------------------------------------------

@pytest.fixture
def server():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(DEFAULT_CSV))
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def get(url):
    try:
        with urllib.request.urlopen(url) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        return e.code, json.load(e)


def test_health(server):
    assert get(f"{server}/health") == (200, {"status": "ok"})


def test_oat_endpoint_reports_sold_out_rows(server):
    status, body = get(f"{server}/milk/oat")
    assert status == 200
    assert body["component"] == "oat_milk"
    assert body["sold_out_count"] == 1
    assert {r["component_id"] for r in body["rows"]} == {"oat_milk"}
    assert [r["store_id"] for r in body["rows"] if r["sold_out"]] == ["10482"]


def test_component_query_matches_oat_shortcut(server):
    assert get(f"{server}/milk?component=oat_milk")[1] == get(f"{server}/milk/oat")[1]


def test_all_milk_endpoint(server):
    status, body = get(f"{server}/milk")
    assert status == 200
    assert body["component"] == "all_milk"
    assert len(body["rows"]) == 9
    # First Hill oat milk + Capitol Hill almond milk
    assert body["sold_out_count"] == 2


def test_unknown_component_returns_400(server):
    status, body = get(f"{server}/milk?component=soy_milk")
    assert status == 400
    assert "soy_milk" in body["error"]


def test_unknown_path_returns_404(server):
    assert get(f"{server}/nope")[0] == 404
