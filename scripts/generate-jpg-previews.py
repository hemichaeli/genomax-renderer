#!/usr/bin/env python3
"""
Generate high-quality JPG previews from production PDFs using PyMuPDF.
300 DPI output, JPEG quality 92.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import fitz  # PyMuPDF
from pathlib import Path

BASE = Path("C:/Projects/GenoMAX2/design-system/production-v3")
DPI = 300
QUALITY = 92

def main():
    pdfs = sorted(BASE.rglob("*.pdf"))
    print(f"Found {len(pdfs)} PDFs to convert")

    done = 0
    errors = 0
    for i, pdf_path in enumerate(pdfs):
        jpg_path = pdf_path.with_suffix('.jpg')

        try:
            doc = fitz.open(str(pdf_path))
            page = doc[0]
            # Render at 300 DPI
            zoom = DPI / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            # Save as JPEG
            pix.save(str(jpg_path), output="jpeg")
            doc.close()
            done += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR: {pdf_path.name}: {e}")

        if (i + 1) % 50 == 0:
            print(f"  [{i+1}/{len(pdfs)}] converted...")

    print(f"\nDone: {done} JPGs, {errors} errors")

if __name__ == "__main__":
    main()
