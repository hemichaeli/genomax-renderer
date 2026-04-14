"""
GenoMAX² Asset Validator — Module B
Validates front.jpg and back.jpg existence for each SKU.
"""
from pathlib import Path
from typing import Dict, List


def validate_assets(model: Dict) -> List[str]:
    """Check that front and back images exist. Returns list of errors."""
    errors = []
    front = Path(model.get("image_front", ""))
    back = Path(model.get("image_back", ""))

    if not front.exists():
        errors.append(f"missing front image: {front}")
    elif front.stat().st_size < 1000:
        errors.append(f"front image too small ({front.stat().st_size} bytes): {front}")

    if not back.exists():
        errors.append(f"missing back image: {back}")
    elif back.stat().st_size < 1000:
        errors.append(f"back image too small ({back.stat().st_size} bytes): {back}")

    return errors


def validate_batch(models: List[Dict]) -> List[Dict]:
    """Validate assets for all models. Updates _status and _error."""
    for model in models:
        if model["_status"] == "BLOCKED":
            continue  # already blocked by catalog validation

        errors = validate_assets(model)
        if errors:
            model["_status"] = "BLOCKED"
            model["_error"] = "; ".join(errors)

    return models
