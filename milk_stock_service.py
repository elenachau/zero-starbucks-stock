#!/usr/bin/env python3
"""Milk stock service.

Reads a store stock snapshot CSV and reports whether milk is in stock.

Available quantity = quantity_on_hand - reserved_quantity.
A milk row is SOLD OUT when available quantity <= 0.

Endpoints:
  GET /health                  -> {"status": "ok"}
  GET /milk                    -> every milk row with its stock status
  GET /milk?component=oat_milk -> only rows for that milk (e.g. oat milk)
  GET /milk/oat                -> shortcut for oat milk rows only

Run:
  python3 milk_stock_service.py [--csv PATH] [--port 8080]
"""

import argparse
import csv
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

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


def make_handler(csv_path):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body):
            data = json.dumps(body, indent=2).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            url = urlparse(self.path)
            if url.path == "/health":
                return self._send(200, {"status": "ok"})

            if url.path in ("/milk", "/milk/oat"):
                component = "oat_milk" if url.path == "/milk/oat" else \
                    parse_qs(url.query).get("component", [None])[0]
                if component and component not in MILK_COMPONENTS:
                    return self._send(400, {
                        "error": f"unknown milk component '{component}'",
                        "valid": sorted(MILK_COMPONENTS),
                    })
                # Re-read on every request so a refreshed snapshot is picked up.
                rows = load_milk_rows(csv_path)
                if component:
                    rows = [r for r in rows if r["component_id"] == component]
                return self._send(200, {
                    "snapshot": str(Path(csv_path).name),
                    "component": component or "all_milk",
                    "sold_out_count": sum(r["sold_out"] for r in rows),
                    "rows": rows,
                })

            self._send(404, {"error": "not found"})

        def log_message(self, fmt, *args):
            print(f"[milk-service] {self.address_string()} {fmt % args}")

    return Handler


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--csv", default=str(DEFAULT_CSV), help="path to stock snapshot CSV")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8080)
    args = p.parse_args()

    load_milk_rows(args.csv)  # fail fast if the CSV is missing or malformed
    server = ThreadingHTTPServer((args.host, args.port), make_handler(args.csv))
    print(f"[milk-service] reading {args.csv}")
    print(f"[milk-service] listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
