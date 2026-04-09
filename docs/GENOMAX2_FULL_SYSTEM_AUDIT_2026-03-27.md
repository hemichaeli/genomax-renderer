# GenoMAX2 FULL SYSTEM AUDIT REPORT

**Date:** 2026-03-27
**Repos:** `hemichaeli/genomax2-api` + `hemichaeli/GenoMAX2`
**Methodology:** 6 parallel audit agents (Data Layer, Backend API, Frontend UX, Supplier/Labels, Cross-System Integrity, Architecture)
**Total Findings:** 9 Critical, 17 High, 12 Medium

---

## 1. CRITICAL FAILURES (Must Fix Before Launch)

### CRIT-01: Frontend Has ZERO Backend API Connection
- **Where:** Entire `genomax2-frontend/src/` directory
- **Problem:** No `fetch()`, no axios, no API base URL. The frontend is a self-contained prototype with 100% hardcoded data. The only external call is `supabase.functions.invoke('ai-health-advisor')`.
- **Impact:** The FastAPI backend is completely disconnected from users. No module data, protocol data, or PDP data flows from API to UI.
- **Fix:** Create `src/lib/api.ts` with `VITE_API_BASE_URL`. Implement React Query hooks for all data.

### CRIT-02: HR-05 (Ashwagandha) Leaks Through 3 Separate Paths
- **Path 1:** `genomax2-frontend/data/translation_layer/protocols.json` — HR-05 in sleep_architecture, male_hormonal, female_hormonal
- **Path 2:** `genomax2-frontend/data/modules/index.json` — HR-05 listed with no exclusion marker
- **Path 3:** `genomax2-api/app/protocol/engine.py` lines 119, 143, 167 — inline fallback still contains HR-05
- **Impact:** A hepatotoxicity-flagged module can reach users via frontend protocol display or backend fallback engine.
- **Fix:** Remove HR-05 from all three locations. Add explicit `EXCLUDED_MODULES = {"HR-05"}` blocklist.

### CRIT-03: Label Renderer Hardcodes "1 Capsule, 60 Servings" for ALL Products
- **Where:** `genomax2-frontend/design/labels_v5.1/render_label.py` line 291
- **Problem:** `supplement_facts = {"Serving Size": "1 Capsule", "Servings": "60"}` is hardcoded. Real products vary: fat-burner-mct is "4 Capsules x 22", magnesium-glycinate is "3 Capsules x 30".
- **Impact:** FDA 21 CFR 101.36 violation. Incorrect dosage instructions on every printed label. Patient safety risk.
- **Fix:** Join against `MODULE_SERVING_NORMALIZED_v1.1.csv` by module_code. Fail render if no match (never fall back to defaults).

### CRIT-04: Clinical Unit Typo — mg/mL Instead of mg/dL
- **Where:** `genomax2-api/app/brain/orchestrate.py` line 379
- **Problem:** Magnesium "optimal" range reports `"mg/mL"` instead of `"mg/dL"`. All other branches (deficient, suboptimal, elevated) correctly use mg/dL.
- **Impact:** 1000x unit error. Medically misleading if displayed to users or clinicians.
- **Fix:** Change `"mg/mL"` → `"mg/dL"` on line 379.

### CRIT-05: No Authentication on API Endpoints
- **Where:** `genomax2-api/main.py` — zero auth middleware
- **Problem:** All endpoints (protocol generation, bloodwork processing, supplier mapping approval) are publicly accessible. No JWT, no API key, no Bearer token validation.
- **Impact:** Anyone can generate protocols, approve supplier mappings, or access health data.
- **Fix:** Add FastAPI dependency injection for JWT/API-key auth on all non-public endpoints.

### CRIT-06: CORS Wildcard + Credentials in Production
- **Where:** `genomax2-api/main.py` line 94-100
- **Problem:** `allow_origins=["*"]` with `allow_credentials=True`.
- **Impact:** Any malicious site can make authenticated cross-origin requests.
- **Fix:** Replace with explicit origin whitelist: `["https://genomax2-frontend.vercel.app", "http://localhost:3000"]`.

### CRIT-07: No Purchase/Checkout/Payment Flow in Frontend
- **Where:** Entire frontend — no Stripe, no cart, no checkout page
- **Problem:** The conversion funnel ends at Results. There is zero mechanism for a user to buy anything.
- **Impact:** Complete revenue block. Cannot generate income from traffic.
- **Fix:** Add pricing page, Stripe integration, clear Assessment → Results → Checkout → Dashboard flow.

### CRIT-08: No Rate Limiting on API
- **Where:** Entire API — zero `slowapi` or throttle middleware
- **Problem:** A single bot can flood expensive operations (OCR via Google Cloud Vision, brain pipeline).
- **Impact:** Cost overruns, denial of service, Google quota exhaustion.
- **Fix:** Add `slowapi` with per-endpoint limits (5/min for OCR, 60/min general).

### CRIT-09: Migration Numbering Conflicts
- **Where:** `genomax2-api/migrations/` — 5 pairs of duplicate prefixes (008, 009, 013, 018, 023)
- **Problem:** Execution order is non-deterministic within same prefix. Gap from 020→023 (missing 021, 022).
- **Impact:** Cannot reproduce database state from scratch. Schema conflicts possible.
- **Fix:** Re-number sequentially with zero-padded prefixes. Add CI validation.

---

## 2. HIGH-RISK ISSUES (Will Likely Break Soon)

| ID | Issue | Location | Impact |
|----|-------|----------|--------|
| H-01 | turmeric-gummies still in 6 rows of MODULE_MAPPING_CLEAN_v1.2.csv as APPROVED handle | Frontend data/modules/ | 404 errors, ghost product served |
| H-02 | Safety gate not wired into pipeline — designed but never called | `safety_gate.py` not invoked by `pipeline.py` | Safety rules in DB not enforced at runtime |
| H-03 | 4 competing server entry points (main.py, api_server.py, server.py, server_api.py) | API repo root | Deployment of wrong app = catastrophic |
| H-04 | 4-way version desync: VERSION=3.23.0, main.py=3.58.1, api_server.py=3.43.0, api_server_version.md=3.25.0 | Multiple files | Cannot determine deployed version |
| H-05 | Upload page does nothing — shows success toast, discards file, Analyze button has no onClick | `Upload.tsx` lines 8-13 | Trust-breaking UX for primary entry point |
| H-06 | Assessment os_type field mismatch — stores `osType` (camelCase), Results reads `os_type` (snake_case) | Assessment.tsx vs Results.tsx | Renders "undefined" to every user |
| H-07 | Age never collected in assessment — gender-specific recommendations never fire (parseInt(undefined)=NaN) | Assessment.tsx / researchKnowledgeBase.ts | Males never get testosterone panel, females never get thyroid |
| H-08 | Results lost on page refresh — data passed via `location.state` only | Results.tsx lines 27-32 | Users lose 9-step assessment on any refresh |
| H-09 | Stale handles in frontend store catalog — omega-3-softgels (corrected handle is omega-3-epa-dha-softgel-capsules) | GENOMAX2_STORE_CATALOG.csv | Broken Supliful links, failed Shopify lookups |
| H-10 | Colostrum misclassified as "Probiotics" in Supliful catalog | GENOMAX2_SUPLIFUL_CATALOG.csv lines 6-7 | Wrong ingredient on Shopify metafields, compliance risk |
| H-11 | Alpha-Lipoic Acid mapped to NAD+ (MT-06) — completely wrong product | MODULE_MAPPING_CLEAN_v1.2.csv | Customer receives NAD+ instead of ALA |
| H-12 | Ashwagandha shopify=1, tiktok=1 in SUPLIFUL_CATALOG despite BLOCKED status | Both repos SUPLIFUL_CATALOG.csv | Automated Shopify sync lists blocked product |
| H-13 | No CI/CD test pipeline — 12 test files never run automatically | .github/workflows/ | Safety-critical health code merged without test gate |
| H-14 | Google Cloud credentials written to plaintext temp file | ocr_parser.py line 108-118 | Credential exposure on shared infrastructure |
| H-15 | Dual database risk — Supabase (frontend) + Railway PostgreSQL (backend) may be separate DBs | Frontend Supabase + Backend DATABASE_URL | Data split across two databases with no sync |
| H-16 | LABEL_DATASET has ~161 rows, not 167 or 169 — 6-8 modules have no label data | LABEL_DATASET_INJECTED_v1.0.csv | Missing labels at launch |
| H-17 | Override system can silently corrupt safety-critical fields (contraindications, safety notes) | catalog/override.py | Malformed Excel upload = patient safety risk |

---

## 3. MEDIUM ISSUES (Optimization + Improvement)

| ID | Issue | Fix |
|----|-------|-----|
| M-01 | Supplier intake module entirely mock-based (4 products, TODO comment) | Deprecate or implement real Supliful API |
| M-02 | Label renderer only handles 6x2.5" — Jar products need 8.5x2.0" | Read dimensions from CSV |
| M-03 | PDP QA validator hardcoded to single product (1 of 169) | Parameterize by module_code |
| M-04 | Supliful validation creates 87 separate HTTP clients (no connection pooling) | Single `httpx.AsyncClient` outside loop |
| M-05 | OSDashboard gender hardcoded to "maximo" with no setter | Read from user context |
| M-06 | Onboarding goals collected then discarded on navigation | Pass to assessment via context |
| M-07 | React Query configured but zero hooks in entire codebase | Use for API integration or remove |
| M-08 | Legacy root CSVs (GENOMAX_FINAL_140.csv, etc.) confuse source of truth | Move to `archive/` directory |
| M-09 | MODULE_MAPPING v1.1 and v1.2 coexist with no deprecation marker | Archive v1.1 |
| M-10 | compose.py return type annotation wrong (2-tuple vs 3-tuple) | Fix type hint |
| M-11 | No connection pooling in migration runner or main application | Add `asyncpg.Pool` |
| M-12 | Monkey-patching in bloodwork engine v2 patches | Refactor to subclass/composition |

---

## 4. ARCHITECTURAL WEAKNESSES

1. **Split-brain architecture**: Backend operates on 50 OS-level IDs (`CV-01`), frontend on 169 designer codes (`CAR-OMEGA-M-049`). The `translation_layer_v1.0.json` is an empty stub in both repos. No machine-readable bridge exists.
2. **4 catalog files diverge silently**: `GENOMAX2_SUPLIFUL_CATALOG.csv` (both repos), `Supliful_GenoMAX_catalog.csv` (125 rows), `GENOMAX2_STORE_CATALOG.csv` (60+ rows). No automated sync.
3. **Frontend is a disconnected prototype**: Built with Lovable.dev, has strong visual design, but zero backend integration. Not production-ready in its current form.
4. **No single entry point discipline**: 5 Python server files in one repo.
5. **Safety relies on data absence, not explicit blocking**: HR-05 is "safe" only because its `supliful_handles` array is empty. No explicit blocklist exists.

---

## 5. UX / CONVERSION GAPS

| Gap | Current State | Revenue Impact |
|-----|---------------|----------------|
| No checkout flow | Assessment → Results → dead end | 100% revenue loss |
| No user auth | Cannot save results, track progress, or return | Users churned every session |
| Upload does nothing | File discarded, Analyze button inert | Primary entry point broken |
| "undefined" on results page | osType/os_type field mismatch | First impression failure |
| Stale dates in MAXync | "Dec 11-17" hardcoded in March 2026 | Looks abandoned |
| No PDP pages | No dynamic product detail pages exist | Cannot display module details |
| Video placeholders empty | Two VideoPlaceholder components with no content | Reduces credibility |

---

## 6. DATA INTEGRITY RISKS

1. **HR-05 in protocols.json** — 3 protocols reference excluded module
2. **turmeric-gummies in 11+ locations** across both repos despite backend removal
3. **Ashwagandha channel flags (shopify=1)** contradict BLOCKED status
4. **FULL_MERGED CSV diverged**: 141 rows in API vs 10 rows in frontend (same filename)
5. **Empty translation layer** — no programmatic path between ID systems
6. **Label data count mismatch** — 161 rows vs expected 167

---

## 7. SCALABILITY LIMITS

| Dimension | Current | Limit |
|-----------|---------|-------|
| Concurrency | Single-process uvicorn, no workers | ~50-100 connections |
| Database | No connection pooling | Exhausts PostgreSQL limits |
| Caching | None | Every request hits DB |
| Rate limiting | None | Single bot can DoS |
| Background tasks | None | OCR/brain blocks event loop |
| Monitoring | Telemetry exists in api_server.py but not registered in main.py | Zero observability |

---

## 8. QUICK WINS (High Impact, Low Effort)

| # | Fix | Effort | Impact |
|---|-----|--------|--------|
| 1 | Change `"mg/mL"` → `"mg/dL"` in orchestrate.py:379 | 1 line | Fixes clinical unit error |
| 2 | Remove HR-05 from protocols.json (3 deletions) | 5 min | Closes safety leakage |
| 3 | Set Ashwagandha shopify=0, tiktok=0 in both SUPLIFUL_CATALOGs | 2 min | Prevents automated listing |
| 4 | Remove turmeric-gummies from MODULE_MAPPING_CLEAN_v1.2.csv (6 rows) | 10 min | Eliminates ghost handle |
| 5 | Fix `allow_origins=["*"]` → explicit whitelist in main.py | 1 line | Closes CORS hole |
| 6 | Update VERSION file to 3.58.1 | 1 line | Fixes version confusion |
| 7 | Fix osType → os_type mismatch in Assessment.tsx | 1 line | Fixes "undefined" bug |
| 8 | Delete server.py, server_api.py, api_server_v3.12.0_PENDING.py | rm 3 files | Eliminates deployment risk |

---

## 9. LONG-TERM RECOMMENDATIONS

1. **Single source of truth pipeline**: `validated_handle_mapping.csv` → auto-generates all other CSVs. CI check validates consistency.
2. **Populate the translation layer**: Export PDP engine data from Python into the JSON files. Make frontend self-sufficient for module display.
3. **Build real frontend integration**: Replace all hardcoded data with API hooks. This is the largest work item.
4. **Add auth + payments**: Supabase Auth → JWT validation on FastAPI → Stripe checkout. This is the revenue path.
5. **Explicit safety blocklist**: `EXCLUDED_MODULES` set in protocol engine, label renderer, and frontend. Defense-in-depth, not data-absence.
6. **CI pipeline**: `pytest` + `mypy` + linting on every PR. No merge without green tests.
7. **Consolidate to one database**: Confirm Supabase and Railway point to same PostgreSQL or migrate to one.
8. **Add monitoring**: Wire telemetry into `main.py`. Configure Railway health checks with DB connectivity validation.

---

## POSITIVE FINDINGS (What Is Working Well)

1. **Routing determinism**: The resolver and orchestrate modules use sorted outputs, stable merge logic, and SHA256 hashing. Same inputs produce same outputs.
2. **HR-05 exclusion in new engine**: `protocol_output.py` and `function_dictionary.py` correctly exclude HR-05 with empty handles and changelog documentation.
3. **turmeric-gummies removed from function dictionary**: Correctly removed in v1.0.2 with BIZ-002 documentation.
4. **Prelaunch audit script**: `scripts/prelaunch_audit.py` is a comprehensive 6-group gate covering catalog, label, mapping, API, supplier, and business rule integrity.
5. **Blood constraint enforcement**: Compose phase correctly implements "blood does not negotiate" — blood constraints always override painpoint and lifestyle signals.
6. **Graceful degradation**: `main.py` uses `_try_include` with error handling for router registration — if one module fails, others still load.
7. **Audit trail architecture**: Orchestrate phase computes and persists signal hashes, output hashes, and constraint lists for traceability.

---

## CONCLUSION

The backend engine is architecturally sound with good engineering rigor in its core decision logic. However, the system is NOT launch-ready. The frontend is a disconnected prototype. Safety-critical data leaks through multiple paths. Labels will print with wrong serving data. There is no auth, no payments, no rate limiting, and no CI.

**Recommended execution order:**
1. Execute the 8 quick wins (1-2 hours total)
2. Wire safety gate into pipeline + add explicit blocklist (1 day)
3. Add auth + CORS fix + rate limiting (2-3 days)
4. Fix label renderer to use real serving data (1 day)
5. Build frontend API integration layer (1-2 weeks)
6. Add auth + payments flow (1-2 weeks)
7. CI pipeline + migration cleanup (1 day)
8. Consolidate server entry points + version management (1 day)
