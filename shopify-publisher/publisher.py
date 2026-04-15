"""
GenoMAX² Publisher — Module D
Selects store, runs publish flow per SKU, manages retry/logging.
"""
import os
import csv
import time
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from shopify_client import ShopifyClient

logger = logging.getLogger("publisher")

# Store configuration from environment
STORES = {
    "maximo": {
        "domain": os.environ.get("SHOPIFY_MAXIMO_STORE_DOMAIN", ""),
        "token": os.environ.get("SHOPIFY_MAXIMO_ACCESS_TOKEN", ""),
    },
    "maxima": {
        "domain": os.environ.get("SHOPIFY_MAXIMA_STORE_DOMAIN", ""),
        "token": os.environ.get("SHOPIFY_MAXIMA_ACCESS_TOKEN", ""),
    },
}

MAX_RETRIES = 1  # retry once on transient failure


def get_client(store_name: str) -> Optional[ShopifyClient]:
    """Get Shopify client for the specified store."""
    store = STORES.get(store_name.lower())
    if not store or not store["domain"] or not store["token"]:
        return None
    return ShopifyClient(store["domain"], store["token"])


def publish_sku(model: Dict, dry_run: bool = False) -> Dict:
    """
    Publish a single SKU to Shopify.
    Returns updated model with _status, _error, _product_id.
    """
    store_name = model.get("shopify_store", "")
    sku = model.get("sku", "?")

    # Skip if already blocked
    if model["_status"] == "BLOCKED":
        return model

    if dry_run:
        model["_status"] = "PUBLISHED_DRAFT"
        model["_product_id"] = "dry_run"
        model["_timestamp"] = datetime.now(timezone.utc).isoformat()
        return model

    client = get_client(store_name)
    if not client:
        model["_status"] = "PUBLISH_FAILED"
        model["_error"] = f"No Shopify credentials for store '{store_name}'"
        return model

    # Step 1: Create/update product as draft
    for attempt in range(MAX_RETRIES + 1):
        success, product_id, error = client.product_set(model)
        if success:
            model["_product_id"] = product_id
            break
        if attempt < MAX_RETRIES and _is_transient(error):
            logger.warning(f"Retry {sku}: {error}")
            time.sleep(2)
            continue
        model["_status"] = "PUBLISH_FAILED"
        model["_error"] = error
        return model

    # Step 2: Upload front image (primary)
    front_ok, front_err = client.upload_media(
        product_id, model["image_front"], alt=f"{model['title']} - Front Label"
    )
    if not front_ok:
        logger.warning(f"Front image failed for {sku}: {front_err}")

    # Step 3: Upload back image (secondary)
    back_ok, back_err = client.upload_media(
        product_id, model["image_back"], alt=f"{model['title']} - Back Label"
    )
    if not back_ok:
        logger.warning(f"Back image failed for {sku}: {back_err}")

    model["_status"] = "PUBLISHED_DRAFT"
    model["_timestamp"] = datetime.now(timezone.utc).isoformat()
    return model


def _is_transient(error: str) -> bool:
    """Check if error is transient (network/timeout)."""
    transient = ["timeout", "connection", "502", "503", "504", "throttl"]
    return any(t in error.lower() for t in transient)


def write_log(models: List[Dict], log_path: str = "publish_log.csv"):
    """Write publish log as CSV."""
    fieldnames = ["sku", "store", "status", "error_message", "product_id", "handle", "timestamp"]
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for m in models:
            writer.writerow({
                "sku": m.get("sku", ""),
                "store": m.get("shopify_store", ""),
                "status": m.get("_status", ""),
                "error_message": m.get("_error", ""),
                "product_id": m.get("_product_id", ""),
                "handle": m.get("handle", ""),
                "timestamp": m.get("_timestamp", datetime.now(timezone.utc).isoformat()),
            })
    logger.info(f"Log written: {log_path} ({len(models)} rows)")
