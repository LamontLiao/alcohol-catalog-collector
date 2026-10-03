from alcohol_catalog.official_sites import classify_results, is_excluded, query_for


def test_query_uses_both_brand_names_and_category():
    row = {"brand": "獭祭", "latin_alias": "DASSAI"}
    assert query_for(row, "清酒") == "獭祭 DASSAI 清酒 brand official website"


def test_excludes_retail_and_social_domains():
    assert is_excluded("https://www.amazon.com/brand")
    assert is_excluded("https://www.instagram.com/brand")
    assert not is_excluded("https://www.dassai.com/cn/")


def test_brand_domain_is_likely_but_not_confirmed():
    row = {"brand": "Bacardi", "latin_alias": ""}
    status, candidates, _ = classify_results([
        {"title": "Bacardi Rum", "url": "https://www.bacardi.com/", "description": "Rum brand"}
    ], row)
    assert status == "likely_official_domain"
    assert candidates[0]["url"] == "https://www.bacardi.com/"


def test_no_result_is_not_claimed_as_no_website():
    status, _, detail = classify_results([], {"brand": "Unknown Label", "latin_alias": ""})
    assert status == "no_official_site_found"
    assert "不代表" in detail

