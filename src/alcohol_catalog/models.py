from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(slots=True)
class Product:
    name: str
    brand: str
    alcohol_type_name: str
    sub_type_name: str = ""
    abv: float | None = None
    volume_ml: int | None = None
    origin: str = ""
    image_filename: str = ""
    product_url: str = ""
    image_source_url: str = ""
    source_name: str = ""
    data_status: str = "unverified"
    is_discontinued_or_limited: str = "unknown"

    def row(self) -> dict:
        return asdict(self)


PRODUCT_FIELDS = list(Product("", "", "").row())

