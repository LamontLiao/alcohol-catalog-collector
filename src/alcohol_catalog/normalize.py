from __future__ import annotations

import re
import unicodedata


PARENS = re.compile(r"[（(]([^()（）]{1,100})[)）]")
SPACE = re.compile(r"\s+")
NOISE = re.compile(r"^[·•.\-_/]+$")


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\u200b", "")
    return SPACE.sub(" ", value).strip(" \t|,，;；")


def brand_aliases(line: str) -> tuple[str, str]:
    line = clean_text(line)
    matches = PARENS.findall(line)
    latin = clean_text(matches[-1]) if matches else ""
    primary = clean_text(PARENS.sub("", line))
    return primary, latin


def brand_key(primary: str, latin: str = "") -> str:
    candidate = latin or primary
    candidate = unicodedata.normalize("NFKD", candidate).casefold()
    return re.sub(r"[^a-z0-9\u4e00-\u9fff\u3040-\u30ff]+", "", candidate)


def suspicious(line: str) -> list[str]:
    reasons: list[str] = []
    if NOISE.fullmatch(line.strip()): reasons.append("punctuation_only")
    if len(line) > 80: reasons.append("possible_ocr_merged_line")
    if len(re.findall(r"[（(]", line)) > 2: reasons.append("multiple_brands_or_aliases")
    if re.search(r"[�¼¾燛燹]", line): reasons.append("possible_ocr_corruption")
    if not re.search(r"[A-Za-z\u4e00-\u9fff\u3040-\u30ff]", line): reasons.append("no_name_characters")
    return reasons


def parse_volume_ml(value: str | None) -> int | None:
    if not value: return None
    text = clean_text(str(value)).lower().replace("毫升", "ml").replace("升", "l")
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|cl|l)\b", text)
    if not m: return None
    amount, unit = float(m.group(1)), m.group(2)
    factor = {"ml": 1, "cl": 10, "l": 1000}[unit]
    result = round(amount * factor)
    return result if 20 <= result <= 10000 else None


def parse_abv(value: str | float | int | None) -> float | None:
    if value is None: return None
    if isinstance(value, (float, int)): number = float(value)
    else:
        m = re.search(r"(\d+(?:\.\d+)?)\s*%", value)
        if not m: return None
        number = float(m.group(1))
    return number if 0 <= number <= 100 else None

