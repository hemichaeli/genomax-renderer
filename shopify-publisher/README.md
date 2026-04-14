# GenoMAX² Shopify Direct Publisher

Publishes product catalog directly to Shopify Admin API as drafts.

## Architecture

```
CSV → catalog_loader → asset_validator → publisher → Shopify GraphQL API
                                                    → publish_log.csv
```

## Modules

| Module | Responsibility |
|--------|---------------|
| `catalog_loader.py` | Load CSV, normalize, validate required fields |
| `asset_validator.py` | Verify front.jpg + back.jpg exist per SKU |
| `shopify_client.py` | GraphQL Admin API: productSet, media upload, metafields |
| `publisher.py` | Store selection, publish flow, retry, logging |
| `run_batch.py` | CLI entry point, batch processing, summary |

## Usage

```bash
# Dry run (validate only)
python run_batch.py --store maximo --file shopify_maximo.csv --dry-run --limit 10

# Live publish (10 SKUs)
python run_batch.py --store maximo --file shopify_maximo.csv --limit 10

# Full catalog
python run_batch.py --store maximo --file shopify_maximo.csv
```

## Environment Variables

```
SHOPIFY_MAXIMO_STORE_DOMAIN=your-maximo-store.myshopify.com
SHOPIFY_MAXIMO_ACCESS_TOKEN=shpat_xxxxx
SHOPIFY_MAXIMA_STORE_DOMAIN=your-maxima-store.myshopify.com
SHOPIFY_MAXIMA_ACCESS_TOKEN=shpat_xxxxx
SHOPIFY_API_VERSION=2026-01
```

## Status Codes

| Status | Meaning |
|--------|---------|
| NEW | Just loaded |
| VALIDATED | Passed all checks |
| BLOCKED | Missing field or asset |
| PUBLISHED_DRAFT | Successfully created as draft |
| PUBLISH_FAILED | API error |

## Log Format

```csv
sku,store,status,error_message,product_id,handle,timestamp
```
