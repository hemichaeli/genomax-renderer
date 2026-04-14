#!/usr/bin/env python3
"""
GenoMAX² Rules Engine — Deterministic Layout Pre-Processor
==========================================================
Runs BEFORE rendering. Validates, trims, cascades, and reports.
Supports batch of 600+ SKUs without manual fixes.

Pipeline:
  RAW SKU → validate → product_name_cascade → density_estimate →
  auto_correct → readability_check → STATUS JSON + modified SKU
"""

import re
import copy

# ═══ FORMAT-SPECIFIC RULES ════════════════════════════════════════════════

FORMAT_RULES = {
    "DROPPER": {
        "pn_max_chars": 28,
        "pn_max_lines": 2,
        "pn_font_cascade": [34, 32, 30, 28],  # px steps
        "pn_zone_w": 450,   # px available for product name
        "sug_max_chars": 120,
        "warn_max_chars": 220,
        "ingr_max_chars": 80,
        "density": "high",  # aggressive trimming
        "min_warn_pt": 6,
        "min_body_pt": 7,
        "back_mode": "short",  # short-copy back
        "priority_trim": ["suggested_use", "warnings", "ingredients"],
    },
    "STRIPS": {
        "pn_max_chars": 24,
        "pn_max_lines": 2,
        "pn_font_cascade": [34, 32, 30, 28],
        "pn_zone_w": 620,
        "sug_max_chars": 90,
        "warn_max_chars": 160,
        "ingr_max_chars": 60,
        "density": "low",   # minimal text only
        "min_warn_pt": 6,
        "min_body_pt": 7,
        "back_mode": "standard",
        "priority_trim": ["suggested_use", "warnings"],
    },
    "POUCH": {
        "pn_max_chars": 40,
        "pn_max_lines": 3,
        "pn_font_cascade": [74, 66, 58, 52],
        "pn_zone_w": 1180,
        "sug_max_chars": 180,
        "warn_max_chars": 300,
        "ingr_max_chars": 150,
        "density": "medium",
        "min_warn_pt": 6,
        "min_body_pt": 7,
        "back_mode": "standard",
        "priority_trim": ["suggested_use", "warnings", "ingredients"],
    },
    "BOTTLE": {
        "pn_max_chars": 50,
        "pn_max_lines": 3,
        "pn_font_cascade": [68, 60, 54, 48],
        "pn_zone_w": 1120,
        "sug_max_chars": 200,
        "warn_max_chars": 400,
        "ingr_max_chars": 200,
        "density": "medium",
        "min_warn_pt": 6,
        "min_body_pt": 7,
        "back_mode": "standard",
        "priority_trim": ["suggested_use", "warnings"],
    },
    "JAR": {
        "pn_max_chars": 30,
        "pn_max_lines": 2,
        "pn_font_cascade": [32, 28, 26, 24],
        "pn_zone_w": 740,
        "sug_max_chars": 60,
        "warn_max_chars": 0,  # JAR back = CTA-only
        "ingr_max_chars": 0,
        "density": "high",
        "min_warn_pt": 6,
        "min_body_pt": 7,
        "back_mode": "cta_only",
        "priority_trim": ["suggested_use"],
    },
}

# ═══ PRODUCT NAME CASCADE ════════════════════════════════════════════════

# Smart break points — prefer breaking AFTER these
BREAK_AFTER = [' + ', ' & ', ' - ', 'MG ', 'MCG ', 'IU ']
BREAK_BEFORE = ['(', 'WITH ', 'FOR ']

def smart_break_name(name, max_chars):
    """Break product name at smart points if too long for single line."""
    if len(name) <= max_chars:
        return [name]

    # Try breaking at preferred points
    best_break = -1
    for bp in BREAK_AFTER:
        idx = name.find(bp)
        if 0 < idx < max_chars and idx > len(name) * 0.3:
            candidate = idx + len(bp)
            if candidate > best_break:
                best_break = candidate

    for bp in BREAK_BEFORE:
        idx = name.find(bp)
        if 0 < idx < max_chars and idx > len(name) * 0.3:
            if idx > best_break:
                best_break = idx

    if best_break > 0:
        return [name[:best_break].strip(), name[best_break:].strip()]

    # Fallback: break at last space before max_chars
    space = name[:max_chars].rfind(' ')
    if space > len(name) * 0.25:
        return [name[:space].strip(), name[space:].strip()]

    return [name[:max_chars].strip(), name[max_chars:].strip()]


def cascade_product_name(name, rules):
    """Apply product name cascade: trim → break → font step."""
    actions = []
    original = name

    # Step 1: Remove parenthetical content if too long
    if len(name) > rules["pn_max_chars"]:
        trimmed = re.sub(r'\s*\([^)]*\)\s*', ' ', name).strip()
        if len(trimmed) < len(name):
            name = trimmed
            actions.append("pn_removed_parenthetical")

    # Step 2: Remove redundant prefixes
    if len(name) > rules["pn_max_chars"]:
        for prefix in ["ADVANCED ", "PREMIUM ", "ULTRA ", "PURE ", "100% "]:
            if name.startswith(prefix):
                name = name[len(prefix):]
                actions.append(f"pn_removed_prefix_{prefix.strip()}")
                break

    # Step 3: Smart line breaking
    lines = smart_break_name(name, rules["pn_max_chars"])
    if len(lines) > rules["pn_max_lines"]:
        lines = lines[:rules["pn_max_lines"]]
        actions.append("pn_truncated_lines")

    # Step 4: Determine font step
    # Estimate: which font size fits the longest line in the zone width?
    # (Approximate: IBM Plex Mono at size S, char width ≈ S * 0.6)
    font_step = 0
    longest_line = max(len(l) for l in lines) if lines else 0
    for i, sz in enumerate(rules["pn_font_cascade"]):
        approx_w = longest_line * sz * 0.62  # monospace approximation
        if approx_w <= rules["pn_zone_w"]:
            font_step = i
            break
        font_step = i

    if font_step > 0:
        actions.append(f"pn_font_step_{font_step}")

    return name, lines, font_step, actions

# ═══ TEXT AUTO-CORRECTION ════════════════════════════════════════════════

FILLER_WORDS = [
    " for optimal ", " for best ", " to support ", " in order to ",
    " that may ", " which can ", " as needed ", " as directed ",
    " to help ", " to promote ", " to maintain ", " to ensure ",
    " including ", " especially ", " particularly ",
]

IMPERATIVE_MAP = {
    "Take two capsules": "Take 2 capsules",
    "Take one capsule": "Take 1 capsule",
    "Take three capsules": "Take 3 capsules",
    "two times daily": "2x daily",
    "three times daily": "3x daily",
    "once daily": "daily",
    "with a meal": "with food",
    "with meals": "with food",
    "or as directed by a healthcare professional": "",
    "or as directed by your healthcare provider": "",
    "or as recommended by a healthcare professional": "",
}

def compress_text(text, max_chars):
    """Compress text to fit within max_chars using deterministic rules."""
    if not text or len(text) <= max_chars:
        return text, False

    original = text
    compressed = text

    # Step 1: Apply imperative conversions
    for long, short in IMPERATIVE_MAP.items():
        compressed = compressed.replace(long, short)

    if len(compressed) <= max_chars:
        return compressed.strip(), compressed != original

    # Step 2: Remove filler words
    for filler in FILLER_WORDS:
        compressed = compressed.replace(filler, " ")

    if len(compressed) <= max_chars:
        return compressed.strip(), True

    # Step 3: Truncate at last sentence boundary
    cut = compressed[:max_chars]
    last_period = cut.rfind('.')
    if last_period > max_chars * 0.4:
        return cut[:last_period + 1].strip(), True

    # Step 4: Truncate at last space
    last_space = cut.rfind(' ')
    if last_space > max_chars * 0.3:
        return cut[:last_space].strip() + ".", True

    return cut.strip(), True


def compress_warnings(text, max_chars):
    """Compress warnings keeping safety-critical content first."""
    if not text or len(text) <= max_chars:
        return text, False

    # Priority order: keep safety statements first
    safety_critical = [
        "Not intended for medical use.",
        "Consult a qualified healthcare professional before use",
        "especially if pregnant, nursing, or taking medication.",
    ]

    # Try keeping only critical warnings
    result_parts = []
    remaining = max_chars
    for stmt in safety_critical:
        if stmt in text and len(stmt) <= remaining:
            result_parts.append(stmt)
            remaining -= len(stmt) + 1

    if result_parts:
        result = ' '.join(result_parts)
        if len(result) <= max_chars:
            return result, True

    # Fallback: standard compression
    return compress_text(text, max_chars)


# ═══ DENSITY ESTIMATOR ════════════════════════════════════════════════════

def estimate_density(sku, fmt, rules):
    """Estimate layout density BEFORE rendering.
    Returns: (density_score, overflow_risk, details)
    density_score: 0.0 (empty) to 1.0+ (overflow)
    """
    # Front panel density
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    bio = sku["front_panel"]["zone_4"].get("biological_system", "")

    front_chars = len(pn) + len(desc) + len(bio)

    # Back panel density
    raw = sku.get("back_panel", {}).get("back_label_text", "")
    back_chars = len(raw)

    # Density thresholds per format
    thresholds = {
        "DROPPER": {"front": 80, "back": 400},
        "STRIPS":  {"front": 60, "back": 350},
        "POUCH":   {"front": 120, "back": 800},
        "BOTTLE":  {"front": 100, "back": 600},
        "JAR":     {"front": 70, "back": 200},
    }

    t = thresholds.get(fmt, thresholds["BOTTLE"])
    front_density = front_chars / t["front"]
    back_density = back_chars / t["back"] if t["back"] > 0 else 0

    overflow_risk = max(front_density, back_density) > 1.0

    return {
        "front_density": round(front_density, 2),
        "back_density": round(back_density, 2),
        "overflow_risk": overflow_risk,
        "front_chars": front_chars,
        "back_chars": back_chars,
    }

# ═══ READABILITY CHECKS ══════════════════════════════════════════════════

def check_readability(sku, fmt, rules, font_sizes_used):
    """Check minimum readability constraints.
    Returns list of violations."""
    violations = []

    # Warning minimum 6pt
    warn_sz = font_sizes_used.get("warnings", 99)
    if warn_sz < rules["min_warn_pt"] * 1.33:  # pt to px approx
        violations.append(f"warnings_below_{rules['min_warn_pt']}pt (actual: {warn_sz}px)")

    # Body minimum 7pt
    body_sz = font_sizes_used.get("body", 99)
    if body_sz < rules["min_body_pt"] * 1.33:
        violations.append(f"body_below_{rules['min_body_pt']}pt (actual: {body_sz}px)")

    # CTA visibility — "THIS IS NOT YOUR FULL PROTOCOL" must be present
    raw = sku.get("back_panel", {}).get("back_label_text", "")
    if "full protocol" not in raw.lower() and "protocol" not in raw.lower():
        violations.append("cta_missing_protocol_reference")

    return violations


# ═══ MAIN PIPELINE ════════════════════════════════════════════════════════

def process_sku(sku, fmt=None):
    """
    Main rules engine pipeline.
    Input: raw SKU dict, optional format override
    Output: (modified_sku, status_report)

    status_report = {
        "status": "PASS" | "WARNING" | "FAIL",
        "format": str,
        "actions_taken": [...],
        "font_sizes": {...},
        "density": {...},
        "violations": [...],
    }
    """
    if fmt is None:
        fmt = sku.get("format", {}).get("label_format", "BOTTLE")

    rules = FORMAT_RULES.get(fmt, FORMAT_RULES["BOTTLE"])
    sku = copy.deepcopy(sku)

    actions = []
    font_sizes = {}
    status = "PASS"

    # ── STEP 1: Product Name Cascade ──
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    new_pn, pn_lines, font_step, pn_actions = cascade_product_name(pn, rules)
    if new_pn != pn:
        sku["front_panel"]["zone_3"]["ingredient_name"] = new_pn
    actions.extend(pn_actions)
    font_sizes["product_name"] = rules["pn_font_cascade"][font_step]
    font_sizes["product_name_lines"] = len(pn_lines)

    # ── STEP 2: Density Estimation ──
    density = estimate_density(sku, fmt, rules)

    # ── STEP 3: Auto-Correct Back Panel Content ──
    raw = sku.get("back_panel", {}).get("back_label_text", "")

    # Parse sections from raw text
    sections = _parse_sections(raw)

    # Compress suggested use
    if sections["suggested_use"] and rules["sug_max_chars"] > 0:
        compressed, changed = compress_text(sections["suggested_use"], rules["sug_max_chars"])
        if changed:
            sections["suggested_use"] = compressed
            actions.append("suggested_use_compressed")

    # Compress warnings
    warn_text = ' '.join(sections["warnings"]) if sections["warnings"] else ""
    if warn_text and rules["warn_max_chars"] > 0:
        compressed, changed = compress_warnings(warn_text, rules["warn_max_chars"])
        if changed:
            sections["warnings"] = [compressed]
            actions.append("warnings_compressed")

    # Compress ingredients
    if sections["ingredients"] and rules["ingr_max_chars"] > 0:
        if len(sections["ingredients"]) > rules["ingr_max_chars"]:
            compressed, changed = compress_text(sections["ingredients"], rules["ingr_max_chars"])
            if changed:
                sections["ingredients"] = compressed
                actions.append("ingredients_compressed")

    # Store processed sections for renderer
    sku["_processed_sections"] = sections

    # ── STEP 4: Determine font sizes for back ──
    BACK_FONT_SIZES = {
        "BOTTLE": {"body": 18, "warnings": 18, "sug": 18},
        "JAR":    {"body": 18, "warnings": 14, "sug": 14},
        "POUCH":  {"body": 18, "warnings": 18, "sug": 18},
        "STRIPS": {"body": 16, "warnings": 16, "sug": 16},
        "DROPPER":{"body": 15, "warnings": 15, "sug": 15},
    }
    bf = BACK_FONT_SIZES.get(fmt, BACK_FONT_SIZES["BOTTLE"])
    font_sizes["body"] = bf["body"]
    font_sizes["warnings"] = bf["warnings"]
    font_sizes["suggested_use"] = bf["sug"]

    # ── STEP 5: Readability Checks ──
    violations = check_readability(sku, fmt, rules, font_sizes)

    # ── STEP 6: Determine Status ──
    if violations:
        status = "FAIL"
    elif actions:
        status = "WARNING"

    report = {
        "status": status,
        "format": fmt,
        "actions_taken": actions,
        "font_sizes": font_sizes,
        "density": density,
        "violations": violations,
    }

    return sku, report


def _parse_sections(raw):
    """Quick section parser for rules engine (doesn't need full parse_back)."""
    sections = {"context": "", "suggested_use": "", "warnings": [], "ingredients": ""}
    cs, buf = None, []
    for line in raw.split('\n'):
        s = line.strip()
        if not s:
            if cs and buf:
                t = ' '.join(buf).strip()
                if cs == "context": sections["context"] = t
                elif cs == "suggested_use":
                    sections["suggested_use"] += (" " + t if sections["suggested_use"] else t)
                elif cs == "warnings":
                    if t: sections["warnings"].append(t)
                elif cs == "ingredients": sections["ingredients"] = t
                buf = []
            continue
        if s in ("This is not your full protocol.", "[QR]", "Scan to begin", "genomax.ai"): continue
        if s.startswith("Distributed by"): continue
        if s == "Suggested Use:":
            if buf and cs:
                t = ' '.join(buf).strip()
                if cs == "context": sections["context"] = t
                buf = []
            cs = "suggested_use"; continue
        elif s == "Warnings:":
            if buf and cs:
                t = ' '.join(buf).strip()
                if cs == "suggested_use":
                    sections["suggested_use"] += (" " + t if sections["suggested_use"] else t)
                buf = []
            cs = "warnings"; continue
        elif s.startswith("Ingredients:"):
            if buf and cs == "warnings":
                t = ' '.join(buf).strip()
                if t: sections["warnings"].append(t)
                buf = []
            cs = "ingredients"
            r = s[len("Ingredients:"):].strip()
            if r: buf.append(r)
            continue
        if cs is None: cs = "context"
        buf.append(s)
    if buf and cs:
        t = ' '.join(buf).strip()
        if cs == "context": sections["context"] = t
        elif cs == "suggested_use":
            sections["suggested_use"] += (" " + t if sections["suggested_use"] else t)
        elif cs == "warnings":
            if t: sections["warnings"].append(t)
        elif cs == "ingredients": sections["ingredients"] = t
    return sections


# ═══ BATCH PROCESSOR ═════════════════════════════════════════════════════

def process_batch(skus, system_name="maximo"):
    """Process a batch of SKUs. Returns list of (sku, report) tuples."""
    results = []
    for sku in skus:
        fmt = sku.get("format", {}).get("label_format", "BOTTLE")
        processed_sku, report = process_sku(sku, fmt)
        report["module_code"] = sku.get("_meta", {}).get("module_code", "?")
        results.append((processed_sku, report))
    return results


def print_batch_report(results):
    """Print formatted batch report."""
    print(f"\n{'='*80}")
    print(f"{'MC':<8}| {'Format':<9}| {'Status':<8}| {'Density':<12}| Actions")
    print(f"{'-'*8}|{'-'*10}|{'-'*9}|{'-'*13}|{'-'*40}")

    counts = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    for sku, r in results:
        mc = r.get("module_code", "?")
        fmt = r.get("format", "?")
        st = r["status"]
        dens = f"F:{r['density']['front_density']:.1f} B:{r['density']['back_density']:.1f}"
        acts = ", ".join(r["actions_taken"][:3]) or "none"
        print(f"{mc:<8}| {fmt:<9}| {st:<8}| {dens:<12}| {acts}")
        counts[st] = counts.get(st, 0) + 1

    print(f"\n{'='*80}")
    print(f"TOTAL: {len(results)} | PASS: {counts['PASS']} | WARNING: {counts['WARNING']} | FAIL: {counts['FAIL']}")
    if counts["FAIL"] > 0:
        print("⚠ FAIL conditions detected — review violations before rendering")


# ═══ STANDALONE TEST ═════════════════════════════════════════════════════

if __name__ == "__main__":
    import json
    from pathlib import Path

    DATA = Path(__file__).resolve().parent.parent / "design-system" / "data"
    for name in ["maximo", "maxima"]:
        fp = DATA / f"production-labels-{name}-v4.json"
        with open(fp, encoding='utf-8') as f:
            data = json.load(f)

        print(f"\n{'#'*80}")
        print(f"  {name.upper()} — {len(data['skus'])} SKUs")
        print(f"{'#'*80}")

        results = process_batch(data["skus"], name)
        print_batch_report(results)
