from __future__ import annotations

import csv
import re
from pathlib import Path

from .brands import load_config
from .http import CachedClient
from .images import download_image
from .models import PRODUCT_FIELDS, Product
from .normalize import brand_key
from .sources import openfoodfacts, wikidata


def slug(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-").lower()
    return value[:80] or "product"


def read_brands(path: Path, category_slug: str) -> list[dict]:
    with path.open(encoding="utf-8-sig") as f:
        return [row for row in csv.DictReader(f) if row["category_slug"] == category_slug and row["clean_status"] != "rejected"]


def dedupe(products: list[Product]) -> list[Product]:
    chosen: dict[tuple, Product] = {}
    rank = {"source_verified": 3, "review_needed": 2, "unverified": 1}
    for p in products:
        key = (brand_key(p.brand), brand_key(p.name), p.volume_ml or 0, round(p.abv or -1, 2))
        old = chosen.get(key)
        if not old or rank.get(p.data_status, 0) > rank.get(old.data_status, 0): chosen[key] = p
    return sorted(chosen.values(), key=lambda p:(p.brand.casefold(), p.name.casefold(), p.volume_ml or 0))


def collect(category_slug: str, brands_csv: Path, config_path: Path, output_dir: Path, pages: int = 8):
    config_all = load_config(config_path)
    _, config = next((k,v) for k,v in config_all.items() if v["slug"] == category_slug)
    client = CachedClient(output_dir / "cache")
    products: list[Product] = []
    verification: list[dict] = []
    for row in read_brands(brands_csv, category_slug):
        name = row["latin_alias"] or row["brand"]
        found: list[Product] = []
        errors: list[str] = []
        try: found.extend(openfoodfacts.collect(client, name, config["alcohol_type_name"], config["accepted_terms"], pages))
        except Exception as exc: errors.append(f"openfoodfacts:{type(exc).__name__}")
        try: found.extend(wikidata.collect_named_products(client, name, config["alcohol_type_name"]))
        except Exception as exc: errors.append(f"wikidata:{type(exc).__name__}")
        products.extend(found)
        verification.append({
            "category_slug": category_slug,
            "raw_name": row["raw_name"],
            "brand": row["brand"],
            "latin_alias": row["latin_alias"],
            "verification_status": "verified_has_category_product" if found else ("source_error" if errors else "no_public_evidence"),
            "matched_product_count_before_dedupe": len(found),
            "sources_checked": "Open Food Facts|Wikidata",
            "errors": "|".join(errors),
        })
    final = dedupe(products)
    image_dir = output_dir / "images" / category_slug
    for index, product in enumerate(final, 1):
        filename, status = download_image(product.image_source_url, image_dir, f"{index:06d}_{slug(product.brand)}_{slug(product.name)}")
        product.image_filename = f"images/{category_slug}/{filename}" if filename else ""
        if not filename and product.image_source_url: product.data_status += f"|image_{status}"
    out = output_dir / f"products_{category_slug}.csv"; out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=PRODUCT_FIELDS); writer.writeheader()
        writer.writerows(p.row() for p in final)
    verify_out = output_dir / f"brand_verification_{category_slug}.csv"
    with verify_out.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(verification[0]) if verification else [])
        writer.writeheader(); writer.writerows(verification)
    return out
