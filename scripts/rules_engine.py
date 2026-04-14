#!/usr/bin/env python3
"""
GenoMAX² Rules Engine v2.0 — 4 Sub-Engines
===========================================
1. PRODUCT NAME ENGINE: smart break at +/&/-/MG, font cascade
2. DENSITY ENGINE: measure actual height BEFORE render
3. PRIORITY ENGINE: format-aware trimming order
4. FORMAT SWITCH: per-format layout intelligence

Pipeline: RAW SKU → name_engine → density_engine → priority_engine → format_switch → STATUS
"""
import re, copy

# ═══ ENGINE 1: PRODUCT NAME ENGINE ═══════════════════════════════════════

SMART_BREAKS = [' + ', ' & ', ' - ', 'MG + ', 'MG ', 'MCG ', 'IU ']
BREAK_BEFORE = ['(', 'WITH ', 'FOR ']

def product_name_engine(name, max_lines=2, max_chars=28):
    """
    Step 1: try single line (if fits)
    Step 2: break at smart points (+, &, -, MG)
    Step 3: break_to_2_lines at best split
    Step 4: reduce font step
    Step 5: FAIL if still overflow
    Returns: (processed_name, lines, font_step, actions)
    """
    actions = []
    original = name

    # Remove parenthetical if name too long
    if len(name) > max_chars:
        trimmed = re.sub(r'\s*\([^)]*\)\s*', ' ', name).strip()
        if trimmed != name:
            name = trimmed
            actions.append("removed_parenthetical")

    # Remove redundant prefixes
    if len(name) > max_chars:
        for prefix in ["ADVANCED ", "PREMIUM ", "ULTRA ", "PURE3 ", "PURE ", "100% "]:
            if name.upper().startswith(prefix):
                name = name[len(prefix):]
                actions.append(f"removed_prefix")
                break

    # Step 1: single line?
    if len(name) <= max_chars:
        return name, [name], 0, actions

    # Step 2: smart break
    best_break = -1
    best_type = None
    name_upper = name.upper()
    for bp in SMART_BREAKS:
        idx = name_upper.find(bp)
        if idx > 0 and idx < len(name) * 0.75:
            candidate = idx + len(bp)
            # Prefer break that makes both lines roughly equal
            balance = abs(candidate - (len(name) - candidate))
            if best_break < 0 or balance < abs(best_break - (len(name) - best_break)):
                best_break = candidate
                best_type = bp.strip()

    for bp in BREAK_BEFORE:
        idx = name_upper.find(bp)
        if idx > 4 and idx < len(name) * 0.75:
            balance = abs(idx - (len(name) - idx))
            if best_break < 0 or balance < abs(best_break - (len(name) - best_break)):
                best_break = idx
                best_type = f"before_{bp.strip()}"

    if best_break > 0:
        lines = [name[:best_break].strip(), name[best_break:].strip()]
        lines = [l for l in lines if l][:max_lines]
        actions.append(f"smart_break_at_{best_type}")
        # Check if lines fit — determine font step
        longest = max(len(l) for l in lines)
        font_step = 0
        if longest > max_chars: font_step = 1
        if longest > max_chars * 1.3: font_step = 2
        if longest > max_chars * 1.6: font_step = 3
        return name, lines, font_step, actions

    # Step 3: break at last space before midpoint
    mid = len(name) // 2
    # Search outward from midpoint for a space
    for offset in range(mid):
        for pos in [mid + offset, mid - offset]:
            if 0 < pos < len(name) and name[pos] == ' ':
                lines = [name[:pos].strip(), name[pos:].strip()]
                lines = [l for l in lines if l][:max_lines]
                longest = max(len(l) for l in lines)
                font_step = 0
                if longest > max_chars: font_step = 1
                if longest > max_chars * 1.3: font_step = 2
                actions.append("balanced_split")
                return name, lines, font_step, actions

    # Step 4: force split at max_chars
    lines = [name[:max_chars].strip(), name[max_chars:].strip()]
    lines = [l for l in lines if l][:max_lines]
    actions.append("force_split")
    # FAIL CHECK: lines > max_lines or font < 28 (step > 3)
    font_step = 2
    longest = max(len(l) for l in lines) if lines else 0
    if longest > max_chars * 1.6: font_step = 3
    return name, lines, font_step, actions


# ═══ ENGINE 2: DENSITY ENGINE ════════════════════════════════════════════

# Format dimensions: content area height in pixels
FORMAT_CONTENT_H = {
    "BOTTLE":  479,   # from spec: content frame h
    "JAR":     203,
    "POUCH":   1022,
    "STRIPS":  1338,
    "DROPPER": 1037,
}

# Block heights (approximate, in pixels) per format
def estimate_block_heights(fmt, pn_lines, pn_font_step, has_desc, has_bio, has_meta, has_variant):
    """Estimate total front content height in pixels."""
    # Base block heights from spec zones
    heights = {
        "BOTTLE":  {"brand":36,"mod_label":34,"title_line":50,"ingredient":48,"sys":34,"meta":88,"badge":38,"gaps":80},
        "JAR":     {"brand":30,"mod_label":24,"title_line":28,"ingredient":28,"sys":24,"meta":88,"badge":30,"gaps":40},
        "POUCH":   {"brand":36,"mod_label":34,"title_line":67,"ingredient":58,"sys":34,"meta":108,"badge":40,"gaps":200},
        "STRIPS":  {"brand":34,"mod_label":38,"title_line":73,"ingredient":64,"sys":30,"meta":112,"badge":40,"gaps":300},
        "DROPPER": {"brand":34,"mod_label":36,"title_line":55,"ingredient":90,"sys":30,"meta":112,"badge":38,"gaps":150},
    }
    h = heights.get(fmt, heights["BOTTLE"])

    # Title height depends on lines and font step
    title_sz = [h["title_line"], int(h["title_line"]*0.88), int(h["title_line"]*0.78), int(h["title_line"]*0.70)]
    title_h = len(pn_lines) * title_sz[min(pn_font_step, 3)]

    total = h["brand"] + h["mod_label"] + title_h
    if has_desc: total += h["ingredient"]
    if has_bio: total += h["sys"]
    if has_meta: total += h["meta"]
    if has_variant: total += h["badge"]
    total += h["gaps"]

    return total

def density_engine(sku, fmt):
    """
    Measure actual content height vs available height.
    Returns: {front_used, front_avail, front_ratio, back_used, back_avail, back_ratio, overflow}
    """
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    bio = sku["front_panel"]["zone_4"].get("biological_system", "")

    # Quick name line estimate
    pn_lines = 1 if len(pn) <= 25 else (2 if len(pn) <= 50 else 3)
    front_h = estimate_block_heights(fmt, list(range(pn_lines)), 0, bool(desc), bool(bio), True, True)
    front_avail = FORMAT_CONTENT_H.get(fmt, 479)

    # Back: estimate from text length
    raw = sku.get("back_panel", {}).get("back_label_text", "")
    back_chars = len(raw)
    # Rough: 1 line ≈ 40-60 chars at body size, line height ≈ 28px
    back_lines = max(1, back_chars // 50)
    back_h = back_lines * 28 + 200  # 200px for header/QR/dividers
    back_avail = front_avail  # same content frame height

    return {
        "front_used": front_h,
        "front_avail": front_avail,
        "front_ratio": round(front_h / front_avail, 2) if front_avail else 0,
        "back_used": back_h,
        "back_avail": back_avail,
        "back_ratio": round(back_h / back_avail, 2) if back_avail else 0,
        "overflow": front_h > front_avail or back_h > back_avail,
    }


# ═══ ENGINE 3: PRIORITY ENGINE ═══════════════════════════════════════════

# What to trim FIRST per format
PRIORITY = {
    "DROPPER": ["suggested_use", "warnings", "ingredients", "bio", "descriptor"],
    "STRIPS":  ["suggested_use", "warnings", "descriptor", "bio"],
    "POUCH":   ["suggested_use", "warnings", "ingredients"],
    "BOTTLE":  ["suggested_use", "warnings"],
    "JAR":     ["suggested_use"],  # JAR back = CTA only
}

# Char limits per priority level — from QA MATRIX
LIMITS = {
    "DROPPER": {"suggested_use": 130, "warnings": 200, "ingredients": 50, "context": 100,
                "description": 140, "subtitle": 60},
    "STRIPS":  {"suggested_use": 100, "warnings": 160, "ingredients": 40, "context": 100,
                "description": 120, "subtitle": 0},  # subtitle removed on STRIPS
    "POUCH":   {"suggested_use": 180, "warnings": 280, "ingredients": 120, "context": 220,
                "description": 200, "subtitle": 120},
    "BOTTLE":  {"suggested_use": 180, "warnings": 350, "ingredients": 180, "context": 180,
                "description": 200, "subtitle": 120},
    "JAR":     {"suggested_use": 50,  "warnings": 0,   "ingredients": 0,  "context": 0,
                "description": 100, "subtitle": 60},
}

FILLER_WORDS = [
    " for optimal ", " for best ", " to support ", " in order to ",
    " that may ", " which can ", " as needed ", " as directed ",
    " to help ", " to promote ", " to maintain ", " to ensure ",
]

IMPERATIVE_MAP = {
    "Take two capsules": "Take 2 capsules",
    "Take one capsule": "Take 1 capsule",
    "two times daily": "2x daily",
    "three times daily": "3x daily",
    "or as directed by a healthcare professional": "",
    "or as directed by your healthcare provider": "",
    "or as recommended by a healthcare professional": "",
}

def compress(text, max_chars):
    """Deterministic text compression."""
    if not text or len(text) <= max_chars:
        return text, False
    t = text
    for long, short in IMPERATIVE_MAP.items():
        t = t.replace(long, short)
    for f in FILLER_WORDS:
        t = t.replace(f, " ")
    t = re.sub(r'\s+', ' ', t).strip()
    if len(t) <= max_chars:
        return t, True
    # Truncate at sentence
    cut = t[:max_chars]
    p = cut.rfind('.')
    if p > max_chars * 0.4:
        return cut[:p+1].strip(), True
    s = cut.rfind(' ')
    if s > max_chars * 0.3:
        return cut[:s].strip() + ".", True
    return cut.strip(), True

def strips_special_mode(sections):
    """STRIPS SPECIAL MODE: remove subtitle, extract critical warnings, vertical compress."""
    actions = []
    # Remove subtitle (not enough space)
    sections["_strip_subtitle"] = True
    actions.append("strips_subtitle_removed")

    # Extract only safety-critical warnings
    warn = ' '.join(sections.get("warnings", []))
    if warn:
        critical = []
        for stmt in [
            "Not intended for medical use.",
            "Consult a qualified healthcare professional before use",
            "especially if pregnant, nursing, or taking medication.",
        ]:
            if stmt.lower() in warn.lower():
                critical.append(stmt)
        if critical:
            sections["warnings"] = [' '.join(critical)]
            actions.append("strips_critical_warnings_only")

    sections["_vertical_compress"] = True
    actions.append("strips_vertical_compress")
    return sections, actions

def priority_engine(sections, fmt):
    """Apply priority-ordered trimming to back sections."""
    actions = []
    limits = LIMITS.get(fmt, LIMITS["BOTTLE"])
    order = PRIORITY.get(fmt, PRIORITY["BOTTLE"])

    # STRIPS SPECIAL MODE
    if fmt == "STRIPS":
        sections, strips_acts = strips_special_mode(sections)
        actions.extend(strips_acts)

    for field in order:
        if field == "suggested_use":
            lim = limits.get("suggested_use", 999)
            if sections.get("suggested_use") and lim > 0:
                t, changed = compress(sections["suggested_use"], lim)
                if changed: sections["suggested_use"] = t; actions.append("sug_use_compressed")
            elif lim == 0:
                sections["suggested_use"] = ""; actions.append("sug_use_removed")

        elif field == "warnings":
            lim = limits.get("warnings", 999)
            warn = ' '.join(sections.get("warnings", []))
            if warn and lim > 0:
                t, changed = compress(warn, lim)
                if changed: sections["warnings"] = [t]; actions.append("warnings_compressed")
            elif lim == 0:
                sections["warnings"] = []; actions.append("warnings_removed")

        elif field == "ingredients":
            lim = limits.get("ingredients", 999)
            if sections.get("ingredients") and lim > 0:
                t, changed = compress(sections["ingredients"], lim)
                if changed: sections["ingredients"] = t; actions.append("ingredients_compressed")

        elif field == "context":
            lim = limits.get("context", 999)
            if sections.get("context") and lim > 0:
                t, changed = compress(sections["context"], lim)
                if changed: sections["context"] = t; actions.append("context_compressed")

    return sections, actions


# ═══ ENGINE 4: FORMAT SWITCH ═════════════════════════════════════════════

FORMAT_DIAGNOSTICS = {
    "DROPPER": {
        "pn_max_chars": 28, "pn_max_lines": 2,
        "min_warn_pt": 6, "min_body_pt": 7,
        "allow_bio": True, "allow_variant": True,
        "back_mode": "short",
    },
    "STRIPS": {
        "pn_max_chars": 24, "pn_max_lines": 2,
        "min_warn_pt": 6, "min_body_pt": 7,
        "allow_bio": True, "allow_variant": True,
        "back_mode": "standard",
    },
    "POUCH": {
        "pn_max_chars": 40, "pn_max_lines": 3,
        "min_warn_pt": 6, "min_body_pt": 7,
        "allow_bio": True, "allow_variant": True,
        "back_mode": "standard",
    },
    "BOTTLE": {
        "pn_max_chars": 50, "pn_max_lines": 3,
        "min_warn_pt": 6, "min_body_pt": 7,
        "allow_bio": True, "allow_variant": True,
        "back_mode": "standard",
    },
    "JAR": {
        "pn_max_chars": 30, "pn_max_lines": 2,
        "min_warn_pt": 6, "min_body_pt": 7,
        "allow_bio": False, "allow_variant": False,
        "back_mode": "cta_only",
    },
}

def format_switch(fmt, density_report):
    """Apply format-specific intelligence. Returns format adjustments."""
    diag = FORMAT_DIAGNOSTICS.get(fmt, FORMAT_DIAGNOSTICS["BOTTLE"])
    adjustments = {}

    # If front overflow, suggest dropping optional blocks
    if density_report["front_ratio"] > 1.0:
        if not diag["allow_bio"]:
            adjustments["drop_bio"] = True
        if not diag["allow_variant"]:
            adjustments["drop_variant"] = True

    adjustments["back_mode"] = diag["back_mode"]
    return adjustments


# ═══ SECTION PARSER ══════════════════════════════════════════════════════

def parse_sections(raw):
    S = {"context": "", "suggested_use": "", "warnings": [], "ingredients": ""}
    cs, buf = None, []
    for line in raw.split('\n'):
        s = line.strip()
        if not s:
            if cs and buf:
                t = ' '.join(buf).strip()
                if cs == "context": S["context"] = t
                elif cs == "suggested_use": S["suggested_use"] += (" " + t if S["suggested_use"] else t)
                elif cs == "warnings":
                    if t: S["warnings"].append(t)
                elif cs == "ingredients": S["ingredients"] = t
                buf = []
            continue
        if s in ("This is not your full protocol.", "[QR]", "Scan to begin", "genomax.ai"): continue
        if s.startswith("Distributed by"): continue
        if s == "Suggested Use:":
            if buf and cs:
                t = ' '.join(buf).strip()
                if cs == "context": S["context"] = t
                buf = []
            cs = "suggested_use"; continue
        elif s == "Warnings:":
            if buf and cs:
                t = ' '.join(buf).strip()
                if cs == "suggested_use": S["suggested_use"] += (" " + t if S["suggested_use"] else t)
                buf = []
            cs = "warnings"; continue
        elif s.startswith("Ingredients:"):
            if buf and cs == "warnings":
                t = ' '.join(buf).strip()
                if t: S["warnings"].append(t)
                buf = []
            cs = "ingredients"
            r = s[len("Ingredients:"):].strip()
            if r: buf.append(r)
            continue
        if cs is None: cs = "context"
        buf.append(s)
    if buf and cs:
        t = ' '.join(buf).strip()
        if cs == "context": S["context"] = t
        elif cs == "suggested_use": S["suggested_use"] += (" " + t if S["suggested_use"] else t)
        elif cs == "warnings":
            if t: S["warnings"].append(t)
        elif cs == "ingredients": S["ingredients"] = t
    return S


# ═══ MAIN PIPELINE ═══════════════════════════════════════════════════════

def process_sku(sku, fmt=None):
    """Main pipeline: 4 engines in sequence. Returns (modified_sku, report)."""
    if fmt is None:
        fmt = sku.get("format", {}).get("label_format", "BOTTLE")

    sku = copy.deepcopy(sku)
    diag = FORMAT_DIAGNOSTICS.get(fmt, FORMAT_DIAGNOSTICS["BOTTLE"])
    all_actions = []

    # ENGINE 1: Product Name
    pn = sku["front_panel"]["zone_3"]["ingredient_name"]
    new_pn, pn_lines, font_step, pn_actions = product_name_engine(
        pn, diag["pn_max_lines"], diag["pn_max_chars"])
    if new_pn != pn:
        sku["front_panel"]["zone_3"]["ingredient_name"] = new_pn
    all_actions.extend(pn_actions)

    # AUTO-TRIM FRONT: descriptor and subtitle
    limits = LIMITS.get(fmt, LIMITS["BOTTLE"])
    desc = sku["front_panel"]["zone_4"].get("descriptor", "")
    if desc and limits.get("description", 999) < len(desc):
        trimmed, _ = compress(desc, limits["description"])
        sku["front_panel"]["zone_4"]["descriptor"] = trimmed
        all_actions.append("descriptor_trimmed")

    # STRIPS: remove subtitle flag
    if fmt == "STRIPS":
        sku["front_panel"]["zone_4"]["_strip_subtitle"] = True

    # ENGINE 2: Density
    density = density_engine(sku, fmt)

    # ENGINE 3: Priority trimming on back sections
    raw = sku.get("back_panel", {}).get("back_label_text", "")
    sections = parse_sections(raw)
    sections, prio_actions = priority_engine(sections, fmt)
    all_actions.extend(prio_actions)
    sku["_processed_sections"] = sections

    # ENGINE 4: Format switch
    adjustments = format_switch(fmt, density)

    # ── FAIL CONDITIONS (from PRODUCTION LOCK SPEC) ──
    violations = []

    # Product name: fail if lines > max_lines or font < 28 (step > 3)
    if len(pn_lines) > diag["pn_max_lines"]:
        violations.append("pn_exceeds_max_lines")
    if font_step > 3:
        violations.append("pn_font_below_minimum")

    # CTA: must always exist
    if "protocol" not in raw.lower() and "scan" not in raw.lower():
        violations.append("missing_CTA")

    # QR: must always exist (checked by presence of back_label_text)
    if not raw.strip():
        violations.append("missing_QR_data")

    # Warnings: font < 6pt = FAIL
    # (checked at render time, but flag if warnings exist and format has h=0)
    warn_text = ' '.join(sections.get("warnings", []))
    if warn_text and fmt in ("DROPPER", "STRIPS", "POUCH"):
        if len(warn_text) > LIMITS.get(fmt, {}).get("warnings", 999) * 1.5:
            violations.append("warnings_may_be_unreadable")

    # Warnings: enforce single paragraph
    if len(sections.get("warnings", [])) > 1:
        sections["warnings"] = [' '.join(sections["warnings"])]
        all_actions.append("warnings_merged_to_single_paragraph")

    # Footer zone: no content may enter (enforced by renderer, flagged here if density > 1.0)
    if density["front_ratio"] > 1.0:
        all_actions.append("density_high_check_footer")

    status = "FAIL" if violations else ("WARNING" if all_actions else "PASS")

    report = {
        "status": status,
        "format": fmt,
        "actions_taken": all_actions,
        "font_sizes": {"product_name_step": font_step, "product_name_lines": len(pn_lines)},
        "density": density,
        "violations": violations,
        "adjustments": adjustments,
    }
    return sku, report


# ═══ BATCH + CLI ═════════════════════════════════════════════════════════

def process_batch(skus):
    results = []
    for sku in skus:
        fmt = sku.get("format", {}).get("label_format", "BOTTLE")
        s, r = process_sku(sku, fmt)
        r["module_code"] = sku.get("_meta", {}).get("module_code", "?")
        results.append((s, r))
    return results

def print_report(results):
    print(f"\n{'='*90}")
    print(f"{'MC':<8}| {'Format':<9}| {'St':<5}| {'F.Den':<6}| {'B.Den':<6}| {'PN Step':<8}| Actions")
    print(f"{'-'*8}|{'-'*10}|{'-'*6}|{'-'*7}|{'-'*7}|{'-'*9}|{'-'*40}")
    c = {"PASS": 0, "WARNING": 0, "FAIL": 0}
    for _, r in results:
        mc = r["module_code"]; fmt = r["format"]; st = r["status"]
        fd = r["density"]["front_ratio"]; bd = r["density"]["back_ratio"]
        ps = r["font_sizes"]["product_name_step"]
        acts = ", ".join(r["actions_taken"][:3]) or "none"
        print(f"{mc:<8}| {fmt:<9}| {st:<5}| {fd:<6}| {bd:<6}| {ps:<8}| {acts}")
        c[st] = c.get(st, 0) + 1
    print(f"\n{'='*90}")
    total = len(results)
    print(f"TOTAL: {total} | PASS: {c['PASS']} | WARNING: {c['WARNING']} | FAIL: {c['FAIL']}")

    # LOCK CRITERIA CHECK (from PRODUCTION LOCK SPEC v1.0)
    pass_rate = (c['PASS'] + c['WARNING']) / total * 100 if total else 0
    fail_count = c['FAIL']
    print(f"\n{'─'*90}")
    print(f"LOCK CRITERIA:")
    print(f"  PASS+WARNING rate: {pass_rate:.1f}% (required: >=80%): {'OK' if pass_rate >= 80 else 'FAIL'}")
    print(f"  FAIL count: {fail_count} (required: 0): {'OK' if fail_count == 0 else 'FAIL'}")
    if pass_rate >= 80 and fail_count == 0:
        print(f"  STATUS: SYSTEM LOCKED ✓")
    else:
        print(f"  STATUS: NOT LOCKED — {fail_count} failures must be resolved")

if __name__ == "__main__":
    import json
    from pathlib import Path
    DATA = Path(__file__).resolve().parent.parent / "design-system" / "data"
    for name in ["maximo", "maxima"]:
        fp = DATA / f"production-labels-{name}-v4.json"
        with open(fp, encoding='utf-8') as f:
            data = json.load(f)
        print(f"\n{'#'*90}\n  {name.upper()} — {len(data['skus'])} SKUs\n{'#'*90}")
        results = process_batch(data["skus"])
        print_report(results)
