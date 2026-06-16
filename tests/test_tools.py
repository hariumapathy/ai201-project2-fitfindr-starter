"""
tests/test_tools.py

Use python -m pytest tests/ to run
"""

from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe


# -- search_listings -----------------------------------------------------------

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []   # empty list, no exception

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)


# -- suggest_outfit --------------------------------------------------------------

def test_suggest_outfit_empty_wardrobe():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    outfit = suggest_outfit(results[0], get_empty_wardrobe())
    assert isinstance(outfit, str)
    assert outfit != ""


# -- create_fit_card -------------------------------------------------------------

def test_create_fit_card_incomplete_outfit():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    fit_card = create_fit_card("", results[0])
    assert isinstance(fit_card, str)
    assert fit_card != ""