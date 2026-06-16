# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

---

## Tool Inventory

### Tool 1: search_listings

**What it does:**
Given a user's description and the size and max price (the latter two may not be specified), search the listings data and find relevant clothing items that fit the description, size, and price criteria.

**Input parameters:**
- `description` (str): A user's description of a clothing item they want to thrift (ex: "vintage baggy tee" or "white sneakers"). This description is required.
- `size` (str): The user's target size, which is not case sensitive (ex: "M", "m", and "S/M" would be considered the same sizes). Examples might include size tags ("S", "L", "XL", etc), size words such as "small", "medium", "large", etc, or size numbers such as waist and leg measurements. If a target size is not specified, the `size` parameter can be set to None.
- `max_price` (float): The maximum (inclusive) price that an item must remain at or below to be a relevant item. If a max price does not need to specified, `max_price` can be set to None.

**What it returns:**
Returns a list of dictionary items, where each dictionary items corresponds to one relevant clothing item. The list is returned in order of relevance, with the first item being the most relevant pick.

Each dict item in the list has the following structure:
{
    "id": str,
    "title": str,
    "description": str,
    "category": str (either "tops", "bottoms", "outerwear", "shoes", "accessories"),
    "style_tags": list[str]
    "size": str,
    "condition": str,
    "price": float,
    "colors": list[str],
    "brand": str,
    "platform": str
  },

**What happens if it fails or returns nothing:**
If the search_listings tool fails or returns an empty list, then the output of the tool call will be an empty list, and this is checked by the agent loop to determine if an error message needs to be added to the session.

If both price and size are specified, then the session's error message might be:

"No relevant items found for '< item description >'. Try removing the size filter or increasing the max price, or add more descriptive keywords."

If only price or size is specified, then the session's error message will omit suggestions related to the unspecified parameter (ex: drop the suggestion of increasing the max price if max_price is None).

In short, the exact wording of the session's error message will vary depending on if the `max_price` and `size` parameters were actually specified in the tool call arguments.

---

### Tool 2: suggest_outfit

**What it does:**
Given a dictionary item, `new_item` and a user's wardrobe (stored as a dict), the suggest_outfit tool returns a string description of a possible outfit, using the new_item and items from the wardrobe.

**Input parameters:**
- `new_item` (dict): A dictionary item, as described in the output of the search_listings tool, containing information about a clothing item.
- `wardrobe` (dict): A dictionary that contains the key "items", which has a list of dict items as its value.

**What it returns:**
Returns a string description of the outfit, clearly mentioning what the components of the outfit are, by synthesizing the overall looks and styles of the different items, while naming each item. The description should also include some explanation as to why the produced outfit works well together.

**What happens if it fails or returns nothing:**
If the wardrobe is empty, then the returned string should be general styling advice for the selected item, rather than outright failing to produce any meaningful output.

For any other failures, an error message of "Unable to create an outfit" is returned, and is caught and handled accordingly in the agent loop.

---

### Tool 3: create_fit_card

**What it does:**
Given an outfit description and the chosen new_item dict, the create_fit_card tool will return a social media caption for the outfit.

**Input parameters:**
- `outfit` (str): The string description of the outfit, provided by the tool suggest_outfit.
- `new_item` (dict): The dict item representing the select item's listing information.
**What it returns:**
Returns a social media-style caption (roughly 2 to 4 sentences) of the provided outfit as a string. This caption should be somewhat creative, flow naturally, and include details such as the new item's price, name, and platform. The caption will include specific terms to capture the overall outfit, and should be different for multiple tool calls.

**What happens if it fails or returns nothing:**
If the tool fails or returns nothing, or if the provided outfit string is empty or just contains whitespace, an error message should be returned: "Unable to generate social media caption". This is then caught and handled in the agent loop.

---

## How the Planning Loop Works

1. Take the user's query, and check that the query is not empty. If empty, set the session error message to "Please enter a description of what you're looking for.". Do not proceed with the tool calls until the user reenters a non-empty query.

2. For a valid user query, parse the description, size, and max_price using an LLM via API calls as a parser, which is given the query as part of its prompt. Then, have the agent use search_listings and pass the parsed description, size, and max_price from the user query (if size and/or max_price is not provided, they are set to None).

3. If search_listings fails or returns an empty list, then add an error message to the session informing that no relevant items were found in the listings data, and to recommend adding more keywords,  removing the size filter, or increasing the max_price, if specified. Do not continue with the tool calls until the user provides a more refined/different query.

4. If search_listings successfully returns a non-empty list, take the first element to be new_item. Pass new_item and the user's wardrobe to suggest_outfit. The user's wardrobe is either an empty or example wardrobe, determined by radio buttons on the UI.

5. If suggest_outfit fails or returns an empty string, then an error message should be added to the session, saying "Unable to create an outfit". If the given wardrobe is empty, the output of the tool call will be general styling advice that is not grounded to a specific wardrobe.

6. If suggest_outfit returns a successful output, pass the output and new_item to create_fit_card. If create_fit_card fails or returns an empty string, then an error message for the session should state "Unable to generate social media caption".

7. Lastly, if create_fit_card returns a successful output, then the entire session should be returned, to be displayed in the corresponding fields of the UI as outputs.

---

## State Management Approach

The state is stored and accessed via the dictionary created by the _new_session method in agent.py.

The below is an example of an initialized session dict:
```
 {
    "query": query,              # original user query
    "parsed": {},                # extracted description / size / max_price
    "search_results": [],        # list of matching listing dicts
    "selected_item": None,       # top result, passed into suggest_outfit
    "wardrobe": wardrobe,        # user's wardrobe dict
    "outfit_suggestion": None,   # string returned by suggest_outfit
    "fit_card": None,            # string returned by create_fit_card
    "error": None,               # set if the interaction ended early
}
```
The query and wardrobe fields are the first to be populated, right after the user provides a query and selects a wardrobe. The wardrobe comes from the data_loader utility functions get_empty_wardrobe() or get_example_wardrobe(), depending on the radio button the user selects. The parsed dict comes from the LLM parser.

 The search_results is updated by the search_listings tool. If search_results is a non-empty list, then the first result in search_results is stored in selected_item. The outfit_suggestion field is updated to be the output of the suggest_outfit tool, which takes selected_item and wardrobe as inputs. The fit_card field is set to the output of the create_fit_card tool, which takes in outfit_suggestion and selected_item.

At any step, if the tool call fails, the session dict is returned, with session["error"] set to some useful string message. For a successful session, session["error"] will be None, and all other fields will be populated / no longer be None or empty.

---

## Error Handling Approach

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Sets `session["error"]` to a message stating no relevant items were found, recommending the user add more keywords to the description and/or increase the max price or drop the size filter (the exact wording adjusts based on whether max_price and/or size were actually specified/found by the parser). For example, the query "designer ballgown size XXS under $5" would result in the following message displayed to the user: "No relevant items found for 'designer ballgown'. Try removing the size filter or increasing the max price, or add more descriptive keywords.".
| suggest_outfit | Wardrobe is empty | Returns general styling advice for the new item alone, rather than a specific outfit combination. It does **not** throw an error or update `session["error"]` with an error message. Instead, the general styling advice will recommend common/general clothing items to go along with the new item, instead of pulling specific items from a populated wardrobe. For example, if the user query is "vintage graphic tee under $30" and the user selects "Empty wardrobe (new user)", the text in the "Outfit Idea" panel might look like this: "This tee would look amazing with some high-waisted jeans or a flowy skirt to balance out the boxy fit, and you could add some edgy boots or sneakers to really bring out the grunge vibe. Pairing it with a leather jacket or a denim jacket would also add a cool layer of depth to the overall look. The black color is pretty versatile, so you could also experiment with popping it against some brighter colored bottoms or shoes for a more playful feel."
| create_fit_card | Outfit input is missing or incomplete |  Sets `session["error"]` to "Unable to generate social media caption". This can be triggered by passing an empty string to the create_fit_card tool, for example. |

---

## Spec Reflection

**One way the spec helped during implementation:**
The spec helped during implementation to understand and map out the agent loop, which was helpful in prompting Claude when implementing the tool functions in tools.py and the run_agent() function in agent.py. By having a diagram of the loop already constructed, it was easier to see how each tool had to perform in isolation, which helped inform testing and ensuring that each tool held to its contract in terms of expected vs actual output/behavior. Instead of having to describe the loop in vague terms, the architecture diagram made it easier to get specific and relevant code snippets from Claude, rather than having Claude make assumptions of its own and incorrectly implement the tools.


**One way the implementation diverged from the spec, and why:**
My implementation slightly diverged from the spec in terms of specificity and the wording of the session's error messages for different tool failures. My spec was not super specific in terms of prompts to LLMs for the tool calls, and how exactly the error messages would be structured. However, the spec served as a foundation upon which I added extra details as I walked through the implementation and flushed out the vague/missing details.

---

## AI Usage
**Instance 1**
- *What I gave the AI:* I gave Claude the Architecture diagram from my planning.md, the Tool 1 info under the Tools section of planning.md, and a description of load_listings() in data_loader.py, and asked it to implement the search_listings tool.
- *What it produced:* It produced an initial draft of the search_listings function and additional helper functions that are now in tools.py.
- *What I changed or overrode:* I further specified how I wanted the size matching to be done, to handle cases such as "S/M" and the user asks for a medium item. This prompted the LLM to further refine the helper functions, specifically _size_matches(), to ensure that "fuzzy" size matching would avoid excessive filtering. I also had Claude explain how the code handling scoring of item relevancy, and how it matched items and dealt with items with similar scores/relevancy.

**Instance 2**

- *What I gave the AI:* I gave Claude the Planning Loop, State Management, Error Handling, and Architecture diagram sections of my planning.md, and asked it to gradually implement run_agent() in agent.py, step by step.
- *What it produced:* It produced a draft of the run_agent() function code, and added a helper function _parse_query() to use an LLM as a parser.
- *What I changed or overrode:* I specified that the Groq API was being used, and asked it to ensure that the LLM parser would act more deterministic, so the temperature parameter was added to the Groq API call and was set to 0.
