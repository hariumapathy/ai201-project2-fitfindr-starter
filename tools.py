"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────
def _tokenize(text: str) -> set[str]:
    """Lowercase and split text into a set of word tokens (alphanumeric only)."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))

def _size_matches(requested_size: str, listing_size: str) -> bool:
    """
    Check whether a requested size matches a listing's size string.

    Matching is case-insensitive and token-based rather than raw substring,
    so "S" matches "S/M" (tokens: {"s", "m"}) but does NOT incorrectly match
    "XS" (tokens: {"xs"}) the way a plain substring check would.

    Listing size strings are split on whitespace, "/", and parentheses,
    e.g. "XL (oversized)" -> {"xl", "oversized"}, "W30 L30" -> {"w30", "l30"}.
    """
    requested = requested_size.strip().lower()
    listing_tokens = set(re.split(r"[\s/()]+", listing_size.lower()))
    listing_tokens.discard("")
    return requested in listing_tokens

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.

    Each listing dict has the following fields:
        id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform

    TODO:
        1. Load all listings with load_listings().
        2. Filter by max_price and size (if provided).
        3. Score each remaining listing by keyword overlap with `description`.
        4. Drop any listings with a score of 0 (no relevant matches).
        5. Sort by score, highest first, and return the listing dicts.

    Before writing code, fill in the Tool 1 section of planning.md.
    """
    if not description or not description.strip():
        return []

    try:
        listings = load_listings()
    except Exception:
        # Treat a data-loading failure the same as "no results" — the agent's
        # error-handling path is the same either way.
        return []

    query_tokens = _tokenize(description)

    candidates = []
    for item in listings:
        # -- price filter (inclusive) --
        if max_price is not None and item.get("price", float("inf")) > max_price:
            continue

        # -- size filter (fuzzy, token-based match) --
        if size is not None:
            item_size = item.get("size") or ""
            if not _size_matches(size, item_size):
                continue

        # -- relevance scoring: keyword overlap across title/description/tags --
        title_tokens = _tokenize(item.get("title", ""))
        desc_tokens = _tokenize(item.get("description", ""))
        tag_tokens = set()
        for tag in item.get("style_tags", []):
            tag_tokens |= _tokenize(tag)

        score = (
            len(query_tokens & title_tokens)
            + len(query_tokens & desc_tokens)
            + len(query_tokens & tag_tokens)
        )

        if score > 0:
            candidates.append((score, item))

    # Sort by score descending; stable sort preserves original order on ties
    candidates.sort(key=lambda pair: pair[0], reverse=True)

    return [item for _score, item in candidates]



# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def _format_item_for_prompt(item: dict, label_keys: tuple[str, ...]) -> str:
    """
    Format a single item dict (listing or wardrobe item) into a compact,
    human-readable line for use inside an LLM prompt.

    Only includes fields that are present and non-null, so missing data
    (e.g. a wardrobe item with notes=None) doesn't pollute the prompt.
    """
    parts = []
    for key in label_keys:
        value = item.get(key)
        if not value:
            continue
        if isinstance(value, list):
            value = ", ".join(value)
        parts.append(f"{key}: {value}")
    return "; ".join(parts)


def _build_outfit_prompt(new_item: dict, wardrobe_items: list[dict]) -> str:
    """Build the LLM prompt for the non-empty-wardrobe case."""
    new_item_desc = _format_item_for_prompt(
        new_item, ("title", "category", "colors", "style_tags", "description")
    )

    wardrobe_lines = []
    for w_item in wardrobe_items:
        line = _format_item_for_prompt(
            w_item, ("name", "category", "colors", "style_tags", "notes")
        )
        wardrobe_lines.append(f"- {line}")
    wardrobe_text = "\n".join(wardrobe_lines)

    return f"""You are a thrift-savvy stylist helping someone figure out how to wear a
new secondhand piece with clothes they already own.

New item they're considering buying:
{new_item_desc}

Their current wardrobe:
{wardrobe_text}

Suggest one complete outfit that pairs the new item with specific pieces from
their wardrobe (name them directly — don't invent items that aren't listed).
Write 2-3 sentences. Describe the overall vibe/style the combination creates
and briefly explain why it works (color, silhouette, or style synergy) —
don't just list the items and their attributes. Write like a friend giving
styling advice, not a product description."""

def _build_general_styling_prompt(new_item: dict) -> str:
    """Build the LLM prompt for the empty-wardrobe case (no items to reference)."""
    new_item_desc = _format_item_for_prompt(
        new_item, ("title", "category", "colors", "style_tags", "description")
    )

    return f"""You are a thrift-savvy stylist. Someone is considering buying this
secondhand piece but hasn't told you what else is in their wardrobe yet:

{new_item_desc}

Since you don't know what they already own, give general styling advice:
what categories of items (e.g. bottoms, shoes, outerwear), colors, or styles
would pair well with this piece, and what overall vibe it could create.
Write 2-3 sentences, like a friend giving advice — not a product description."""




def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1-2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    if not new_item:
        return "Unable to create an outfit"

    wardrobe_items = (wardrobe or {}).get("items", [])

    if wardrobe_items:
        prompt = _build_outfit_prompt(new_item, wardrobe_items)
    else:
        prompt = _build_general_styling_prompt(new_item)

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200,
        )
        result = response.choices[0].message.content.strip()
        if not result:
            return "Unable to create an outfit"
        return result
    except Exception:
        return "Unable to create an outfit"



# ── Tool 3: create_fit_card ───────────────────────────────────────────────────
def _build_fit_card_prompt(outfit: str, new_item: dict) -> str:
    """Build the LLM prompt for generating a shareable outfit caption."""
    title = new_item.get("title", "this piece")
    price = new_item.get("price")
    platform = new_item.get("platform", "")

    price_str = f"${price:.0f}" if isinstance(price, (int, float)) else "an unknown price"

    return f"""Write a short, casual social media caption (2-4 sentences) for an
Instagram or TikTok "outfit of the day" post featuring a thrifted item.

Item: {title}
Price: {price_str}
Platform: {platform}

Outfit styling notes:
{outfit}

The caption should:
- Sound like a real person posting about their thrifted find, not a product
  listing or advertisement
- Naturally mention the item name, price, and platform once each — woven into
  the sentence, not listed
- Capture the specific vibe/style of the outfit in a few words
- Feel casual and a little fun — emojis are okay if they fit naturally, but
  don't overdo it

Write only the caption text, nothing else."""


def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Unable to generate social media caption"

    if not new_item:
        return "Unable to generate social media caption"

    prompt = _build_fit_card_prompt(outfit, new_item)

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=1.0,
            max_tokens=150,
        )
        result = response.choices[0].message.content.strip()
        if not result:
            return "Unable to generate social media caption"
        return result
    except Exception:
        return "Unable to generate social media caption"


if __name__=="__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
    results = search_listings('graphic tee', 'S', 100)

    #print(results)

    outfit = suggest_outfit(results[0], get_empty_wardrobe())
    print(outfit)

    #print(create_fit_card(outfit, results[0]))

    print(create_fit_card("", results[0]))