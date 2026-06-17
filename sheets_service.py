"""
sheets_service.py  –  TrendyKBot
---------------------------------
Reads product/stock data from Google Sheets using a Service Account.

Expected sheet columns (headers in row 1):
  No. | Product_Code | Product Name | Brand Name | Product Type |
  Size | Available Count | Expiry Date
"""

import os
import logging

import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_client = None
_sheet  = None


def _get_sheet():
    """Initialize and return the first worksheet of the Google Sheet."""
    global _client, _sheet
    if _sheet is not None:
        return _sheet

    email    = os.getenv("GOOGLE_SERVICE_ACCOUNT_EMAIL", "").strip()
    raw_key  = os.getenv("GOOGLE_PRIVATE_KEY", "")
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()

    if not (email and raw_key and sheet_id):
        raise RuntimeError(
            "❌ Google Sheets credentials missing.\n"
            "Please set GOOGLE_SERVICE_ACCOUNT_EMAIL, GOOGLE_PRIVATE_KEY "
            "and GOOGLE_SHEET_ID in your .env file."
        )

    private_key = raw_key.replace("\\n", "\n")

    creds = Credentials.from_service_account_info(
        {
            "type": "service_account",
            "project_id": "trendyk-bot",
            "private_key_id": "key",
            "private_key": private_key,
            "client_email": email,
            "token_uri": "https://oauth2.googleapis.com/token",
        },
        scopes=SCOPES,
    )

    _client = gspread.authorize(creds)
    spreadsheet = _client.open_by_key(sheet_id)
    _sheet = spreadsheet.sheet1
    logger.info("✅ Connected to Google Sheet: %s", spreadsheet.title)
    return _sheet


# ─────────────────────────── Public helpers ───────────────────────────────────

def get_all_products() -> list[dict]:
    """Return all product rows as a list of dicts."""
    try:
        ws = _get_sheet()
        rows = ws.get_all_records()
        products: list[dict] = []
        for row in rows:
            name = str(row.get("Product Name", "")).strip()
            if not name:
                continue
            products.append(
                {
                    "id":           str(row.get("Product_Code") or row.get("No.", "")).strip(),
                    "name":         name,
                    "category":     str(row.get("Brand Name", "")).strip(),
                    "product_type": str(row.get("Product Type", "")).strip(),
                    "size":         str(row.get("Size", "")).strip(),
                    "available":    str(row.get("Available Count", "")).strip(),
                    "expiry":       str(row.get("Expiry Date", "")).strip(),
                }
            )
        return products
    except Exception as exc:
        logger.error("Error fetching products: %s", exc)
        return []


def _is_available(product: dict) -> bool:
    try:
        return int(product["available"]) > 0
    except (ValueError, TypeError):
        return True


def get_categories() -> list[str]:
    """Return sorted, deduplicated Brand Name values that have stock."""
    products = get_all_products()
    seen: list[str] = []
    for p in products:
        cat = p["category"]
        if cat and cat not in seen and _is_available(p):
            seen.append(cat)
    return seen


def get_product_types() -> list[str]:
    """Return sorted, deduplicated Product Type values that have stock."""
    products = get_all_products()
    seen: list[str] = []
    for p in products:
        pt = p["product_type"]
        if pt and pt not in seen and _is_available(p):
            seen.append(pt)
    return seen


def get_products_by_category(category: str) -> list[dict]:
    """Return all products that belong to *category* (Brand Name) and have stock."""
    return [
        p for p in get_all_products()
        if p["category"].lower() == category.lower() and _is_available(p)
    ]


def get_products_by_type(product_type: str) -> list[dict]:
    """Return all products that belong to *product_type* and have stock."""
    return [
        p for p in get_all_products()
        if p["product_type"].lower() == product_type.lower() and _is_available(p)
    ]


def get_product_by_id(product_id: str) -> dict | None:
    """Return a single product dict by its id, or None."""
    for p in get_all_products():
        if p["id"] == product_id:
            return p
    return None
