from __future__ import annotations

from urllib.parse import quote

from ..models import Product
from ..normalize import clean_text, parse_abv, parse_volume_ml


API = "https://world.openfoodfacts.org/api/v2/search"


def collect(client, brand: str, alcohol_type: str, accepted_terms: list[str], pages: int = 8):
    for page in range(1, pages + 1):
        data = client.json(API, {
            "brands_tags": brand,
            "page": page,
            "page_size": 100,
            "fields": "code,product_name,product_name_en,brands,categories,categories_tags,quantity,alcohol_value,countries,image_front_url,url",
        })
        products = data.get("products", [])
        if not products: break
        for item in products:
            categories = " ".join(item.get("categories_tags") or []) + " " + str(item.get("categories") or "")
            if not any(term.casefold() in categories.casefold() for term in accepted_terms):
                continue
            name = clean_text(item.get("product_name_en") or item.get("product_name") or "")
            if not name: continue
            volume = parse_volume_ml(item.get("quantity"))
            yield Product(
                name=name, brand=clean_text(item.get("brands") or brand).split(",")[0],
                alcohol_type_name=alcohol_type, sub_type_name=_subtype(categories, accepted_terms),
                abv=parse_abv(item.get("alcohol_value")), volume_ml=volume,
                origin=clean_text(item.get("countries") or ""), product_url=item.get("url") or f"https://world.openfoodfacts.org/product/{quote(str(item.get('code','')))}",
                image_source_url=item.get("image_front_url") or "", source_name="Open Food Facts",
                data_status="source_verified",
            )


def _subtype(categories: str, terms: list[str]) -> str:
    return next((term for term in terms if term.casefold() in categories.casefold()), "")

