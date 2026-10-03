from alcohol_catalog.normalize import brand_aliases, brand_key, parse_abv, parse_volume_ml


def test_aliases():
    assert brand_aliases("麦卡伦 （MACALLAN）") == ("麦卡伦", "MACALLAN")


def test_key():
    assert brand_key("", "The Glenlivet") == "theglenlivet"


def test_volume():
    assert parse_volume_ml("70 cl") == 700
    assert parse_volume_ml("1.5 L") == 1500


def test_abv():
    assert parse_abv("40% vol") == 40.0

