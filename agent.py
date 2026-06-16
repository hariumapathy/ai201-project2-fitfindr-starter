"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import os
import re

from dotenv import load_dotenv
from groq import Groq

from tools import search_listings, suggest_outfit, create_fit_card

load_dotenv()


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.

    You may add fields to this dict as needed for your implementation.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query
    using the LLM. Missing fields default to None.

    Returns a dict: {"description": str, "size": str | None, "max_price": float | None}
    Falls back to treating the whole query as the description if parsing fails.
    """
    fallback = {"description": query.strip(), "size": None, "max_price": None}

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return fallback

    prompt = f"""Extract a clothing search from this user query. Return ONLY a JSON
object with exactly these keys: "description" (string — the core item being
searched for, e.g. "vintage graphic tee"), "size" (string or null if not
mentioned), "max_price" (number or null if not mentioned, no dollar sign).

Query: "{query}"

Respond with ONLY the JSON object, no other text."""

    try:
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=150,
        )
        raw = response.choices[0].message.content.strip()
        raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.MULTILINE).strip()

        import json
        parsed = json.loads(raw)

        description = parsed.get("description") or query.strip()
        size = parsed.get("size") or None
        max_price = parsed.get("max_price")
        max_price = float(max_price) if max_price is not None else None

        return {"description": description, "size": size, "max_price": max_price}
    except Exception:
        # Parsing failed for any reason (bad JSON, API error, etc.) — fall back
        # to using the raw query as the description with no size/price filter.
        return fallback

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.

    TODO — implement this function using the planning loop you designed in planning.md:

        Step 1: Initialize the session with _new_session().

        Step 2: Parse the user's query to extract a description, size, and
                max_price. You can use regex, string splitting, or ask the LLM
                to parse it — document your choice in planning.md.
                Store the result in session["parsed"].

        Step 3: Call search_listings() with the parsed parameters.
                Store results in session["search_results"].
                If no results: set session["error"] to a helpful message and
                return the session early. Do NOT proceed to suggest_outfit
                with empty input.

        Step 4: Select the item to use (e.g., the top result).
                Store it in session["selected_item"].

        Step 5: Call suggest_outfit() with the selected item and wardrobe.
                Store the result in session["outfit_suggestion"].

        Step 6: Call create_fit_card() with the outfit suggestion and selected item.
                Store the result in session["fit_card"].

        Step 7: Return the session.

    Before writing code, complete the Planning Loop and State Management sections
    of planning.md — your implementation should match what you described there.
    """
    session = _new_session(query, wardrobe)

    # Step 1: guard against an empty/invalid query
    if not query or not query.strip():
        session["error"] = "Please enter a description of what you're looking for."
        return session

    # Step 2: parse the query into description / size / max_price
    session["parsed"] = _parse_query(query)

    # Step 3: call search_listings
    session["search_results"] = search_listings(
        description=session["parsed"]["description"],
        size=session["parsed"]["size"],
        max_price=session["parsed"]["max_price"],
    )

    if not session["search_results"]:
        size = session["parsed"]["size"]
        max_price = session["parsed"]["max_price"]
        suggestions = []
        if size is not None:
            suggestions.append("removing the size filter")
        if max_price is not None:
            suggestions.append("increasing the max price")
        if suggestions:
            suggestion_text = " or ".join(suggestions)
            session["error"] = (
                f"No relevant items found for '{session['parsed']['description']}'. "
                f"Try {suggestion_text}, or add more descriptive keywords."
            )
        else:
            session["error"] = (
                f"No relevant items found for '{session['parsed']['description']}'. "
                f"Try adding more descriptive keywords."
            )
        return session

    # Step 4: select the top result
    session["selected_item"] = session["search_results"][0]

    # Step 5: call suggest_outfit
    outfit_suggestion = suggest_outfit(session["selected_item"], session["wardrobe"])

    if not outfit_suggestion or outfit_suggestion == "Unable to create an outfit":
        session["error"] = "We couldn't put together an outfit for this item. Please try again."
        return session

    session["outfit_suggestion"] = outfit_suggestion

    # Step 6: call create_fit_card
    fit_card = create_fit_card(session["outfit_suggestion"], session["selected_item"])

    if not fit_card or fit_card == "Unable to generate social media caption":
        session["error"] = "We couldn't generate a caption for this outfit. Please try again."
        return session

    session["fit_card"] = fit_card

    # Step 7: return the completed session
    return session



# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")

    #print(session)
    print()

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")

    #print(session2)
    print()
