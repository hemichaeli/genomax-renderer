#!/usr/bin/env python3
"""
GenoMAX² Naming Migration Tracker
===================================
Adds function_name_locked, naming_status, naming_version to all SKUs.
Tracks: legacy → hero_locked → final_locked

Usage:
  python naming_migration.py --report          # Show current status
  python naming_migration.py --lock-heroes     # Lock 12 Hero SKUs
  python naming_migration.py --export          # Export migration CSV
"""
import json
import csv
import argparse
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "design-system" / "data"
CATALOG_DIR = BASE / "catalog"

# 12 Hero SKUs — function-first naming
HERO_SKUS = {
    "CV-01": {"function_name_locked": "Lipid Metabolism Module", "format": "BOTTLE"},
    "CV-04": {"function_name_locked": "Gut Motility Module", "format": "JAR"},
    "GL-01": {"function_name_locked": "Glucose Regulation Module", "format": "DROPPER"},
    "GL-04": {"function_name_locked": "Iron Status Module", "format": "STRIPS"},
    "GL-10": {"function_name_locked": "Oral Microbiome Module", "format": "BOTTLE"},
    "MT-04": {"function_name_locked": "Metabolic Support Module", "format": "POUCH"},
    "MT-09": {"function_name_locked": "Muscle Protein Synthesis Module", "format": "POUCH"},
    "IN-04": {"function_name_locked": "Respiratory Defense Module", "format": "DROPPER"},
    "COG-01": {"function_name_locked": "Cognitive Function Module", "format": "STRIPS"},
    "SL-01": {"function_name_locked": "Sleep Architecture Module", "format": "BOTTLE"},
    "HR-02": {"function_name_locked": "Hormonal Balance Module", "format": "BOTTLE"},
    "IN-03": {"function_name_locked": "Immune Optimization Module", "format": "STRIPS"},
}

NAMING_VERSION = "v3.1"


def load_all_skus():
    """Load all SKUs from JSON source of truth."""
    all_skus = []
    for sys_name in ["maximo", "maxima"]:
        fp = DATA_DIR / f"production-labels-{sys_name}-v4.json"
        if not fp.exists():
            continue
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        for sku in data["skus"]:
            sku["_system"] = sys_name
            all_skus.append(sku)
    return all_skus


def get_naming_status(module_code):
    """Determine naming status for a module code."""
    if module_code in HERO_SKUS:
        return "hero_locked"
    return "legacy"


def generate_report(skus):
    """Generate naming migration diagnostics."""
    total = len(skus)
    hero_locked = 0
    final_locked = 0
    legacy = 0
    by_system = {}

    for sku in skus:
        mc = sku["_meta"]["module_code"]
        sys_code = mc.split("-")[0]
        status = get_naming_status(mc)

        if status == "hero_locked":
            hero_locked += 1
        elif status == "final_locked":
            final_locked += 1
        else:
            legacy += 1

        if sys_code not in by_system:
            by_system[sys_code] = {"total": 0, "hero": 0, "legacy": 0}
        by_system[sys_code]["total"] += 1
        if status == "hero_locked":
            by_system[sys_code]["hero"] += 1
        else:
            by_system[sys_code]["legacy"] += 1

    print("=" * 60)
    print("GenoMAX\u00b2 NAMING MIGRATION REPORT")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Version: {NAMING_VERSION}")
    print("=" * 60)
    print(f"\n  Total active modules:    {total}")
    print(f"  Hero locked:             {hero_locked}")
    print(f"  Final locked:            {final_locked}")
    print(f"  Remaining legacy:        {legacy}")
    print(f"  Migration progress:      {(hero_locked + final_locked) / total * 100:.1f}%")

    print(f"\n  By System:")
    print(f"  {'System':<8} {'Total':<8} {'Hero':<8} {'Legacy':<8}")
    print(f"  {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
    for sys_code in sorted(by_system.keys()):
        s = by_system[sys_code]
        print(f"  {sys_code:<8} {s['total']:<8} {s['hero']:<8} {s['legacy']:<8}")

    print(f"\n  Hero SKUs:")
    for mc, info in sorted(HERO_SKUS.items()):
        print(f"    {mc:<8} {info['format']:<8} {info['function_name_locked']}")

    return {
        "total": total,
        "hero_locked": hero_locked,
        "final_locked": final_locked,
        "legacy": legacy,
        "progress_pct": round((hero_locked + final_locked) / total * 100, 1),
    }


def export_migration_csv(skus, output_path=None):
    """Export full migration status as CSV."""
    if output_path is None:
        output_path = CATALOG_DIR / "naming_migration.csv"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fields = ["module_code", "os", "format", "current_name", "function_name_locked",
              "naming_status", "naming_version"]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for sku in skus:
            mc = sku["_meta"]["module_code"]
            status = get_naming_status(mc)
            hero = HERO_SKUS.get(mc, {})
            writer.writerow({
                "module_code": mc,
                "os": sku["_meta"]["os"],
                "format": sku["format"]["label_format"],
                "current_name": sku["front_panel"]["zone_3"]["ingredient_name"],
                "function_name_locked": hero.get("function_name_locked", ""),
                "naming_status": status,
                "naming_version": NAMING_VERSION if status != "legacy" else "",
            })

    print(f"\nExported: {output_path} ({len(skus)} rows)")


def main():
    parser = argparse.ArgumentParser(description="GenoMAX\u00b2 Naming Migration Tracker")
    parser.add_argument("--report", action="store_true", help="Show migration report")
    parser.add_argument("--export", action="store_true", help="Export migration CSV")
    parser.add_argument("--lock-heroes", action="store_true", help="Display hero lock status")
    args = parser.parse_args()

    skus = load_all_skus()

    if not any([args.report, args.export, args.lock_heroes]):
        args.report = True  # default

    if args.report or args.lock_heroes:
        generate_report(skus)

    if args.export:
        export_migration_csv(skus)


if __name__ == "__main__":
    main()
