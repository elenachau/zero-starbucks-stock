import pytest
from fastapi.testclient import TestClient

from milk_stock_service import create_app, load_milk_rows

HEADER = (
    "store_id,store_name,store_open,component_id,component_name,component_type,"
    "quantity_on_hand,reserved_quantity,last_updated_at\n"
)

# Test-only stock data. The committed stock snapshot was removed; store IDs follow the mobile
# orders CSV (data/mobile_orders_2025-03-03_to_09.csv).
SAMPLE_ROWS = [
    # SB-10482: oat milk sold out (0 on hand, 0 reserved)
    "SB-10482,Store SB-10482,true,oat_milk,Oatmilk,drink_base,0,0,2025-03-07T06:35:00-08:00",
    "SB-10482,Store SB-10482,true,almond_milk,Almondmilk,drink_base,38,1,2025-03-07T06:41:05-08:00",
    "SB-10482,Store SB-10482,true,two_pct_milk,2% Milk,drink_base,96,3,2025-03-07T06:43:40-08:00",
    "SB-10482,Store SB-10482,true,caramel_drizzle,Caramel Drizzle,add_in,52,1,2025-03-07T06:37:31-08:00",
    # SB-11937: 1 oat milk left (2 on hand, 1 reserved); almond milk sold out
    "SB-11937,Store SB-11937,true,oat_milk,Oatmilk,drink_base,2,1,2025-03-07T06:44:02-08:00",
    "SB-11937,Store SB-11937,true,almond_milk,Almondmilk,drink_base,0,0,2025-03-07T06:31:27-08:00",
    "SB-11937,Store SB-11937,true,two_pct_milk,2% Milk,drink_base,104,3,2025-03-07T06:42:36-08:00",
    # SB-20516: closed, everything in stock
    "SB-20516,Bellevue Square,false,oat_milk,Oatmilk,drink_base,72,0,2025-03-07T06:27:10-08:00",
    "SB-20516,Bellevue Square,false,almond_milk,Almondmilk,drink_base,54,0,2025-03-07T06:27:38-08:00",
    "SB-20516,Bellevue Square,false,two_pct_milk,2% Milk,drink_base,120,0,2025-03-07T06:26:55-08:00",
]


def write_csv(tmp_path, *rows):
    path = tmp_path / "stock.csv"
    path.write_text(HEADER + "".join(r + "\n" for r in rows), encoding="utf-8")
    return path


@pytest.fixture
def sample_csv(tmp_path):
    return write_csv(tmp_path, *SAMPLE_ROWS)


def oat_row(store_id, on_hand, reserved, store_open="true"):
    return (
        f"{store_id},Store {store_id},{store_open},oat_milk,Oatmilk,drink_base,"
        f"{on_hand},{reserved},2025-03-07T06:00:00-08:00"
    )


# --- load_milk_rows ------------------------------------------------------------

def test_oat_milk_sold_out_status(sample_csv):
    oat = {r["store_id"]: r for r in load_milk_rows(sample_csv) if r["component_id"] == "oat_milk"}

    assert set(oat) == {"SB-10482", "SB-11937", "SB-20516"}

    assert oat["SB-10482"]["available_quantity"] == 0
    assert oat["SB-10482"]["sold_out"] is True

    # 2 on hand, 1 reserved -> 1 available, not sold out
    assert oat["SB-11937"]["available_quantity"] == 1
    assert oat["SB-11937"]["sold_out"] is False

    assert oat["SB-20516"]["available_quantity"] == 72
    assert oat["SB-20516"]["sold_out"] is False
    assert oat["SB-20516"]["store_open"] is False


def test_only_milk_components_are_returned(sample_csv):
    rows = load_milk_rows(sample_csv)
    assert {r["component_id"] for r in rows} == {"oat_milk", "almond_milk", "two_pct_milk"}
    assert len(rows) == 9  # 3 milks x 3 stores; caramel drizzle is skipped


def test_store_id_kept_exactly_as_in_file(sample_csv):
    ids = {r["store_id"] for r in load_milk_rows(sample_csv)}
    assert ids == {"SB-10482", "SB-11937", "SB-20516"}


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
    path = write_csv(tmp_path, oat_row("SB-1", on_hand, reserved))
    [row] = load_milk_rows(path)
    assert row["available_quantity"] == available
    assert row["sold_out"] is sold_out


# --- configuration -------------------------------------------------------------

def test_app_refuses_to_start_without_stock_csv(monkeypatch):
    monkeypatch.delenv("STOCK_SNAPSHOT_CSV", raising=False)
    with pytest.raises(RuntimeError, match="STOCK_SNAPSHOT_CSV"):
        create_app()


def test_app_reads_stock_csv_from_env(monkeypatch, sample_csv):
    monkeypatch.setenv("STOCK_SNAPSHOT_CSV", str(sample_csv))
    body = TestClient(create_app()).get("/milk/oat").json()
    assert body["sold_out_count"] == 1


# --- HTTP service ----------------------------------------------------------------

@pytest.fixture
def client(sample_csv):
    return TestClient(create_app(sample_csv))


def get(client, path):
    resp = client.get(path)
    return resp.status_code, resp.json()


def test_health(client):
    assert get(client, "/health") == (200, {"status": "ok"})


def test_oat_endpoint_reports_sold_out_rows(client):
    status, body = get(client, "/milk/oat")
    assert status == 200
    assert body["component"] == "oat_milk"
    assert body["sold_out_count"] == 1
    assert {r["component_id"] for r in body["rows"]} == {"oat_milk"}
    assert [r["store_id"] for r in body["rows"] if r["sold_out"]] == ["SB-10482"]


def test_component_query_matches_oat_shortcut(client):
    assert get(client, "/milk?component=oat_milk")[1] == get(client, "/milk/oat")[1]


def test_all_milk_endpoint(client):
    status, body = get(client, "/milk")
    assert status == 200
    assert body["component"] == "all_milk"
    assert len(body["rows"]) == 9
    # SB-10482 oat milk + SB-11937 almond milk
    assert body["sold_out_count"] == 2


def test_unknown_component_returns_400(client):
    status, body = get(client, "/milk?component=soy_milk")
    assert status == 400
    assert "soy_milk" in body["error"]


def test_unknown_path_returns_404(client):
    assert client.get("/nope").status_code == 404
