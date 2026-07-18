import os
import re

import barcode
from barcode.writer import ImageWriter


def safe_filename(value: str) -> str:
    """Turn a SKU into a filesystem-safe stem (letters, digits, dash, underscore)."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", value)


def generate_barcode(value: str, out_dir: str) -> str:
    """
    Render `value` (a product SKU) as a scannable Code128 barcode PNG inside `out_dir`.
    Code128 is used because it encodes full alphanumeric SKUs, not just digits.
    Returns the saved file's path.
    """
    os.makedirs(out_dir, exist_ok=True)

    code128 = barcode.get("code128", value, writer=ImageWriter())
    stem = os.path.join(out_dir, safe_filename(value))

    saved_path = code128.save(stem, options={
        "write_text": True,
        "module_height": 12.0,
        "font_size": 9,
        "text_distance": 4.0,
        "quiet_zone": 4.0,
    })
    return saved_path
