#!/usr/bin/env python3
"""Milk stock service (FastAPI).

Reads a store stock snapshot CSV and reports whether milk is in stock.

Available quantity = quantity_on_hand - reserved_quantity.
A milk row is SOLD OUT when available quantity <= 0.

Endpoints:
  GET /health                  -> {"status": "ok"}
  GET /milk                    -> every milk row with its stock status
  GET /milk?component=oat_milk -> only rows for that milk (e.g. oat milk)
  GET /milk/oat                -> shortcut for oat milk rows only

Run:
  uvicorn milk_stock_service:app --port 8080
  (set STOCK_SNAPSHOT_CSV to read a different snapshot)
"""

import csv
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import JSONResponse

DEFAULT_CSV = Path(__file__).parent / "data" / "stock_snapshot_2025-03-07_0645.csv"
MILK_COMPONENTS = {"oat_milk", "almond_milk", "two_pct_milk"}


def load_milk_rows(csv_path):
    """Read the snapshot and return milk rows with calculated availability."""
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["component_id"] not in MILK_COMPONENTS:
                continue
            on_hand = int(r["quantity_on_hand"])
            reserved = int(r["reserved_quantity"])
            available = on_hand - reserved
            rows.append({
                "store_id": r["store_id"],  # kept as string to preserve leading zeros
                "store_name": r["store_name"],
                "store_open": r["store_open"].strip().lower() == "true",
                "component_id": r["component_id"],
                "component_name": r["component_name"],
                "quantity_on_hand": on_hand,
                "reserved_quantity": reserved,
                "available_quantity": available,
                "sold_out": available <= 0,
                "last_updated_at": r["last_updated_at"],
            })
    return rows


def create_app(csv_path=None):
    csv_path = Path(csv_path or os.environ.get("STOCK_SNAPSHOT_CSV", DEFAULT_CSV))
    load_milk_rows(csv_path)  # fail fast if the CSV is missing or malformed

    app = FastAPI(title="Milk stock service")

    def milk_response(component):
        if component and component not in MILK_COMPONENTS:
            return JSONResponse(status_code=400, content={
                "error": f"unknown milk component '{component}'",
                "valid": sorted(MILK_COMPONENTS),
            })
        # Re-read on every request so a refreshed snapshot is picked up.
        rows = load_milk_rows(csv_path)
        if component:
            rows = [r for r in rows if r["component_id"] == component]
        return {
            "snapshot": csv_path.name,
            "component": component or "all_milk",
            "sold_out_count": sum(r["sold_out"] for r in rows),
            "rows": rows,
        }

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/milk")
    def milk(component: Optional[str] = None):
        return milk_response(component)

    @app.get("/milk/oat")
    def milk_oat():
        return milk_response("oat_milk")

    return app


app = create_app()
