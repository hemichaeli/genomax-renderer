#!/usr/bin/env python3
"""
GenoMAX² Batch Publisher — Module E
Main entry point. Loads CSV, validates, publishes in batches, writes summary.

Usage:
  python run_batch.py --store maximo --file shopify_maximo.csv [--dry-run] [--limit 10]
  python run_batch.py --store maxima --file shopify_maxima.csv [--dry-run] [--limit 10]
"""
import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

from catalog_loader import load_store_catalog, load_store_from_github, check_handle_uniqueness
from asset_validator import validate_batch
from publisher import publish_sku, write_log

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("run_batch")


def main():
    parser = argparse.ArgumentParser(description="GenoMAX\u00b2 Shopify Batch Publisher")
    parser.add_argument("--store", required=True, choices=["maximo", "maxima"],
                        help="Target Shopify store")
    parser.add_argument("--file", default=None,
                        help="Path to store-specific CSV (e.g., shopify_maximo.csv)")
    parser.add_argument("--from-github", action="store_true",
                        help="Fetch CSV directly from GitHub raw URL (no local file needed)")
    parser.add_argument("--assets", default="assets",
                        help="Path to assets directory (default: assets)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate only, don't publish to Shopify")
    parser.add_argument("--limit", type=int, default=0,
                        help="Limit number of SKUs to process (0 = all)")
    parser.add_argument("--log", default=None,
                        help="Path to output log CSV (default: publish_log_{store}_{timestamp}.csv)")
    args = parser.parse_args()

    # Resolve source
    assets_dir = Path(args.assets)
    source = "GitHub" if args.from_github else (args.file or "")

    if not args.from_github and not args.file:
        logger.error("Must specify --file or --from-github")
        sys.exit(1)

    if args.file and not args.from_github:
        csv_path = Path(args.file)
        if not csv_path.exists():
            logger.error(f"CSV file not found: {csv_path}")
            sys.exit(1)

    mode = "DRY RUN" if args.dry_run else "LIVE PUBLISH"
    print("=" * 70)
    print(f"GenoMAX\u00b2 Shopify Publisher \u2014 {mode}")
    print(f"Store: {args.store}")
    print(f"Source: {source}")
    print(f"Assets: {assets_dir}")
    print("=" * 70)

    # Phase 1: Load & validate catalog
    if args.from_github:
        logger.info(f"Fetching {args.store} catalog from GitHub...")
        models = load_store_from_github(args.store, str(assets_dir))
    else:
        logger.info(f"Loading {args.file}...")
        models = load_store_catalog(str(args.file), args.store, str(assets_dir))
    models = check_handle_uniqueness(models)
    logger.info(f"Loaded {len(models)} SKUs")

    # Phase 2: Validate assets
    logger.info("Validating assets...")
    models = validate_batch(models)

    # Apply limit
    if args.limit > 0:
        models = models[:args.limit]
        logger.info(f"Limited to {args.limit} SKUs")

    # Phase 3: Publish
    stats = {"NEW": 0, "VALIDATED": 0, "BLOCKED": 0, "PUBLISHED_DRAFT": 0, "PUBLISH_FAILED": 0}
    for i, model in enumerate(models):
        sku = model["sku"]
        status = model["_status"]
        print(f"  [{i+1}/{len(models)}] {sku:<40} {status}", end="")

        if status == "BLOCKED":
            stats["BLOCKED"] += 1
            print(f"  \u2192 BLOCKED: {model['_error'][:60]}")
            continue

        model = publish_sku(model, dry_run=args.dry_run)
        models[i] = model
        final_status = model["_status"]
        stats[final_status] = stats.get(final_status, 0) + 1
        print(f"  \u2192 {final_status}")

    # Phase 4: Write log
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    log_path = args.log or f"publish_log_{args.store}_{ts}.csv"
    write_log(models, log_path)

    # Summary
    print(f"\n{'='*70}")
    print(f"SUMMARY:")
    for status, count in stats.items():
        if count > 0:
            print(f"  {status}: {count}")
    print(f"  TOTAL: {len(models)}")
    print(f"  LOG: {log_path}")

    blocked = stats.get("BLOCKED", 0)
    failed = stats.get("PUBLISH_FAILED", 0)
    if blocked > 0 or failed > 0:
        print(f"\n\u26a0 {blocked} BLOCKED + {failed} FAILED \u2014 review log for details")
    else:
        print(f"\n\u2705 All SKUs processed successfully")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
