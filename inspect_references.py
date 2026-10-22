"""Report basic text-extraction diagnostics for PDFs in data/references."""

from pathlib import Path
import sys

import pymupdf


REFERENCE_DIR = Path(__file__).resolve().parent / "data" / "references"
PREVIEW_LENGTH = 500


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    pdf_paths = sorted(REFERENCE_DIR.glob("*.pdf"))
    if not pdf_paths:
        print(f"No PDF files found in {REFERENCE_DIR}")
        return 1

    for pdf_path in pdf_paths:
        with pymupdf.open(pdf_path) as document:
            page_texts = [page.get_text("text") for page in document]

        extracted_text = "\n".join(page_texts)
        readable_text = " ".join(extracted_text.split())
        empty_pages = [
            str(page_number)
            for page_number, text in enumerate(page_texts, start=1)
            if not text.strip()
        ]
        low_text_pages = [
            str(page_number)
            for page_number, text in enumerate(page_texts, start=1)
            if 0 < len(text.strip()) < 100
        ]

        print(f"\n{pdf_path.name}")
        print(f"  Pages: {len(page_texts)}")
        print(f"  Extracted characters: {len(extracted_text)}")
        print(f"  Extracted words: {len(extracted_text.split())}")
        print(f"  Pages with no extracted text: {', '.join(empty_pages) or 'none'}")
        print(f"  Possible low-text pages (<100 characters): {', '.join(low_text_pages) or 'none'}")
        print(f"  Preview: {readable_text[:PREVIEW_LENGTH]}")
        if len(readable_text) > PREVIEW_LENGTH:
            print("  Preview truncated.")

    print("\nThis text-only check does not validate table structure or numerical accuracy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
