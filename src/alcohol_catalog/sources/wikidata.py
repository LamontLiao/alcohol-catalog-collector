from __future__ import annotations

from ..models import Product
from ..normalize import clean_text


SEARCH = "https://www.wikidata.org/w/api.php"


def resolve_brand(client, query: str) -> list[dict]:
    data = client.json(SEARCH, {"action":"wbsearchentities", "search":query, "language":"en", "uselang":"en", "type":"item", "limit":10, "format":"json"})
    return data.get("search", [])


def collect_named_products(client, brand: str, alcohol_type: str):
    # Wikidata search is used as a conservative supplement. Results without a
    # clear product description remain review candidates rather than verified.
    for hit in resolve_brand(client, brand):
        description = clean_text(hit.get("description") or "")
        if not any(word in description.casefold() for word in ("whisky","whiskey","vodka","gin","rum","tequila","mezcal","liqueur","brandy","cognac","sake")):
            continue
        yield Product(name=clean_text(hit.get("label") or ""), brand=brand,
            alcohol_type_name=alcohol_type, product_url=hit.get("concepturi") or "",
            source_name="Wikidata", data_status="review_needed")

