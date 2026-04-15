#!/usr/bin/env python3
"""
GenoMAX² Catalog Generator
===========================
Source of Truth: JSON files in design-system/data/
Output: CSV files in catalog/

Flow: JSON → CSV → GitHub → Publisher → Shopify

Usage:
  python generate_catalog.py              # Generate all 3 CSVs
  python generate_catalog.py --push       # Generate + git add + commit + push
"""
import json
import csv
import argparse
import subprocess
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "design-system" / "data"
CATALOG_DIR = BASE / "catalog"

JSON_SOURCES = {
    "maximo": DATA_DIR / "production-labels-maximo-v4.json",
    "maxima": DATA_DIR / "production-labels-maxima-v4.json",
}

CSV_FIELDS = [
    "sku", "title", "handle", "shopify_store", "environment", "format",
    "price", "system", "function_name", "ingredient_name_label",
    "ingredient_descriptor", "net_quantity", "suggested_use", "contraindications",
]


def json_to_rows(json_path: Path, store_name: str) -> list:
    """Convert JSON SKU data to CSV rows."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for sku in data["skus"]:
        m = sku["_meta"]
        fp = sku["front_panel"]
        fmt = sku["format"]["label_format"]
        st = "MO" if "MAXimo" in m["os"] else "MA"
        ing = fp["zone_3"]["ingredient_name"]
        safe = ing.replace("/", "_").replace(" ", "_").replace(":", "")[:50]
        sku_id = f"{m['module_code']}_{st}_{safe}"

        handle = (
            ing.lower()
            .replace(" ", "-").replace("+", "-").replace("&", "-")
            .replace("(", "-").replace(")", "").replace("--", "-")
            .strip("-")[:60]
        )
        handle = f"{handle}-{store_name}"

        row = {
            "sku": sku_id,
            "title": f"{ing} ({m['os']})",
            "handle": handle,
            "shopify_store": store_name,
            "environment": m["os"],
            "format": fmt,
            "price": "",
            "system": m["module_code"].split("-")[0],
            "function_name": fp["zone_6"]["function"]["value"],
            "ingredient_name_label": ing,
            "ingredient_descriptor": fp["zone_4"].get("descriptor", ""),
            "net_quantity": fp["zone_7"]["net_quantity"].replace("DIETARY SUPPLEMENT \u00b7 ", ""),
            "suggested_use": "",
            "contraindications": "",
        }
        rows.append(row)
    return rows


def write_csv(filepath: Path, rows: list):
    """Write rows to CSV."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  {filepath.name}: {len(rows)} rows")


def main():
    parser = argparse.ArgumentParser(description="Generate catalog CSVs from JSON source of truth")
    parser.add_argument("--push", action="store_true", help="Git add + commit + push after generation")
    args = parser.parse_args()

    print("=" * 60)
    print("GenoMAX\u00b2 Catalog Generator")
    print(f"Source: {DATA_DIR}")
    print(f"Output: {CATALOG_DIR}")
    print("=" * 60)

    all_rows = []
    maximo_rows = []
    maxima_rows = []

    for store_name, json_path in JSON_SOURCES.items():
        if not json_path.exists():
            print(f"  WARNING: {json_path} not found, skipping")
            continue
        rows = json_to_rows(json_path, store_name)
        all_rows.extend(rows)
        if store_name == "maximo":
            maximo_rows = rows
        else:
            maxima_rows = rows

    write_csv(CATALOG_DIR / "products_master.csv", all_rows)
    write_csv(CATALOG_DIR / "shopify_maximo.csv", maximo_rows)
    write_csv(CATALOG_DIR / "shopify_maxima.csv", maxima_rows)

    print(f"\nTotal: {len(all_rows)} SKUs ({len(maximo_rows)} maximo + {len(maxima_rows)} maxima)")

    if args.push:
        print("\nPushing to GitHub...")
        subprocess.run(["git", "add", "catalog/"], cwd=str(BASE), check=True)
        subprocess.run(
            ["git", "commit", "-m", "Regenerate catalog CSVs from JSON source"],
            cwd=str(BASE), check=True
        )
        subprocess.run(
            ["git", "push", "-u", "origin", "claude/implement-design-system-nFj8Y"],
            cwd=str(BASE), check=True
        )
        print("Pushed to GitHub.")


if __name__ == "__main__":
    main()
