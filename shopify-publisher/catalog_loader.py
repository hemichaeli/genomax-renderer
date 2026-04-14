"""
GenoMAX² Catalog Loader — Module A
Reads store-specific CSVs, normalizes to internal model, validates required fields.
"""
import csv
from pathlib import Path
from typing import List, Dict, Optional


REQUIRED_FIELDS = ["sku", "title", "handle", "shopify_store"]

INTERNAL_MODEL_KEYS = [
    "sku", "title", "handle", "shopify_store", "environment", "format",
    "price", "image_front", "image_back", "system", "function_name",
    "ingredient_name_label", "ingredient_descriptor", "net_quantity",
    "front_label_text", "back_label_text", "suggested_use", "contraindications",
]


def load_csv(filepath: str) -> List[Dict]:
    """Load CSV file and return list of row dicts."""
    rows = []
    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def normalize_row(row: Dict, store_name: str, assets_dir: str = "assets") -> Dict:
    """Normalize a CSV row to the internal model."""
    sku = row.get("sku", "").strip()
    model = {
        "sku": sku,
        "title": row.get("title", "").strip(),
        "handle": row.get("handle", "").strip(),
        "shopify_store": row.get("shopify_store", store_name).strip().lower(),
        "environment": row.get("environment", "MAXimo\u00b2").strip(),
        "format": row.get("format", "BOTTLE").strip().upper(),
        "price": row.get("price", "").strip(),
        "image_front": str(Path(assets_dir) / sku / "front.jpg"),
        "image_back": str(Path(assets_dir) / sku / "back.jpg"),
        "system": row.get("system", "").strip(),
        "function_name": row.get("function_name", "").strip(),
        "ingredient_name_label": row.get("ingredient_name_label", "").strip(),
        "ingredient_descriptor": row.get("ingredient_descriptor", "").strip(),
        "net_quantity": row.get("net_quantity", "").strip(),
        "front_label_text": row.get("front_label_text", "").strip(),
        "back_label_text": row.get("back_label_text", "").strip(),
        "suggested_use": row.get("suggested_use", "").strip(),
        "contraindications": row.get("contraindications", "").strip(),
        "_status": "NEW",
        "_error": "",
    }
    return model


def validate_row(row: Dict) -> List[str]:
    """Validate required fields. Returns list of error messages."""
    errors = []
    for field in REQUIRED_FIELDS:
        if not row.get(field):
            errors.append(f"missing required field: {field}")
    # Handle uniqueness is checked at batch level
    return errors


def load_store_catalog(filepath: str, store_name: str, assets_dir: str = "assets") -> List[Dict]:
    """Load and normalize a store-specific CSV. Returns list of validated models."""
    raw_rows = load_csv(filepath)
    models = []
    for row in raw_rows:
        model = normalize_row(row, store_name, assets_dir)
        errors = validate_row(model)
        if errors:
            model["_status"] = "BLOCKED"
            model["_error"] = "; ".join(errors)
        else:
            model["_status"] = "VALIDATED"
        models.append(model)
    return models


def check_handle_uniqueness(models: List[Dict]) -> List[Dict]:
    """Check that handles are unique within the same store."""
    seen = {}
    for model in models:
        store = model["shopify_store"]
        handle = model["handle"]
        key = f"{store}:{handle}"
        if key in seen:
            model["_status"] = "BLOCKED"
            model["_error"] += f"; duplicate handle '{handle}' in store '{store}'"
        else:
            seen[key] = model["sku"]
    return models
