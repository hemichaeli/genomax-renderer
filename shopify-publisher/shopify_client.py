"""
GenoMAX² Shopify Client — Module C
GraphQL Admin API client for product create/update, media upload, metafields.
Uses productSet mutation for sync-style upsert.
"""
import os
import json
import time
import base64
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

logger = logging.getLogger("shopify_client")

API_VERSION = os.environ.get("SHOPIFY_API_VERSION", "2026-01")


class ShopifyClient:
    def __init__(self, store_domain: str, access_token: str):
        self.store_domain = store_domain.rstrip("/")
        self.access_token = access_token
        self.endpoint = f"https://{self.store_domain}/admin/api/{API_VERSION}/graphql.json"

    def _gql(self, query: str, variables: Dict = None) -> Dict:
        """Execute a GraphQL query against Shopify Admin API."""
        payload = json.dumps({"query": query, "variables": variables or {}}).encode()
        req = Request(self.endpoint, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("X-Shopify-Access-Token", self.access_token)

        try:
            with urlopen(req, timeout=30) as resp:
                return json.loads(resp.read())
        except HTTPError as e:
            body = e.read().decode() if e.fp else ""
            logger.error(f"Shopify HTTP {e.code}: {body[:500]}")
            raise
        except URLError as e:
            logger.error(f"Shopify network error: {e.reason}")
            raise

    def product_set(self, model: Dict) -> Tuple[bool, str, str]:
        """Create or update a product as DRAFT using productSet.
        Returns: (success, product_id, error_message)"""
        tags = self._build_tags(model)
        metafields = self._build_metafields(model)

        mutation = """
        mutation productSet($input: ProductSetInput!) {
          productSet(input: $input) {
            product {
              id
              handle
              status
            }
            userErrors {
              field
              message
            }
          }
        }
        """

        variables = {
            "input": {
                "title": model["title"],
                "handle": model["handle"],
                "status": "DRAFT",
                "tags": tags,
                "metafields": metafields,
                "variants": [{
                    "optionValues": [{"name": "Default", "optionName": "Title"}],
                    "sku": model["sku"],
                    "price": model.get("price") or "0.00",
                }],
            }
        }

        try:
            result = self._gql(mutation, variables)
            data = result.get("data", {}).get("productSet", {})
            errors = data.get("userErrors", [])
            if errors:
                msg = "; ".join(e["message"] for e in errors)
                return False, "", msg
            product = data.get("product", {})
            return True, product.get("id", ""), ""
        except Exception as e:
            return False, "", str(e)

    def upload_media(self, product_id: str, image_path: str, alt: str = "") -> Tuple[bool, str]:
        """Upload an image to a product. Returns (success, error_message)."""
        path = Path(image_path)
        if not path.exists():
            return False, f"Image not found: {image_path}"

        # Stage upload
        stage_mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
          stagedUploadsCreate(input: $input) {
            stagedTargets {
              url
              resourceUrl
              parameters { name value }
            }
            userErrors { field message }
          }
        }
        """

        stage_vars = {
            "input": [{
                "resource": "IMAGE",
                "filename": path.name,
                "mimeType": "image/jpeg",
                "httpMethod": "POST",
            }]
        }

        try:
            result = self._gql(stage_mutation, stage_vars)
            targets = result.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets", [])
            if not targets:
                return False, "No staged upload target returned"

            target = targets[0]
            resource_url = target["resourceUrl"]

            # Upload file to staged URL
            import urllib.request
            import mimetypes
            boundary = "----GenoMAXBoundary"
            body_parts = []
            for param in target["parameters"]:
                body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{param["name"]}"\r\n\r\n{param["value"]}')
            with open(path, "rb") as f:
                file_data = f.read()
            body_parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\nContent-Type: image/jpeg\r\n\r\n')
            body = "\r\n".join(body_parts).encode() + file_data + f"\r\n--{boundary}--\r\n".encode()

            upload_req = Request(target["url"], data=body, method="POST")
            upload_req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
            with urlopen(upload_req, timeout=60) as resp:
                pass  # 200/201 = success

            # Attach to product
            attach_mutation = """
            mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
              productCreateMedia(productId: $productId, media: $media) {
                media { id status }
                mediaUserErrors { field message }
              }
            }
            """
            attach_vars = {
                "productId": product_id,
                "media": [{
                    "originalSource": resource_url,
                    "mediaContentType": "IMAGE",
                    "alt": alt,
                }]
            }
            result = self._gql(attach_mutation, attach_vars)
            media_errors = result.get("data", {}).get("productCreateMedia", {}).get("mediaUserErrors", [])
            if media_errors:
                return False, "; ".join(e["message"] for e in media_errors)

            return True, ""
        except Exception as e:
            return False, str(e)

    def _build_tags(self, model: Dict) -> list:
        """Build deterministic tags."""
        tags = []
        env = model.get("environment", "")
        if env: tags.append(env)
        sys = model.get("system", "")
        if sys: tags.append(sys)
        fmt = model.get("format", "")
        if fmt: tags.append(f"format:{fmt.lower()}")
        tags.append("status:production")
        return tags

    def _build_metafields(self, model: Dict) -> list:
        """Build metafields for the product."""
        ns = "custom"
        fields = []
        mapping = {
            "module_code": model.get("sku", "").split("_")[0] if "_" in model.get("sku", "") else model.get("sku", ""),
            "environment": model.get("environment", ""),
            "system": model.get("system", ""),
            "function_name": model.get("function_name", ""),
            "ingredient_descriptor": model.get("ingredient_descriptor", ""),
            "suggested_use": model.get("suggested_use", ""),
            "contraindications": model.get("contraindications", ""),
            "render_version": "v7",
            "qa_status": "PASS",
        }
        for key, value in mapping.items():
            if value:
                fields.append({
                    "namespace": ns,
                    "key": key,
                    "value": value,
                    "type": "single_line_text_field",
                })
        return fields
