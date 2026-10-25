#!/usr/bin/env python3
"""Generate the static First foods companion site from content JSON."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CONTENT = ROOT / "content"
DIST = ROOT / "dist"
ASSETS = ROOT / "assets"

CATEGORIES = {
    "simple-purees": "Simple purées",
    "mixed-purees": "Mixed purées",
    "finger-foods": "Soft pieces",
    "toddler-meals": "Toddler meals",
    "snacks": "Snacks",
    "celebrations": "Celebrations",
    "basics": "Basics",
    "allergens": "Allergen practice",
}
VERDICTS = {
    "sound": "Sound idea",
    "adjust": "Adjusted",
    "replace": "Replaced",
}
ALLERGENS = {
    "milk",
    "egg",
    "gluten",
    "fish",
    "crustacean",
    "peanut",
    "tree-nut",
    "sesame",
    "soy",
    "mustard",
    "celery",
    "sulphite",
}
RECIPE_KEYS = {
    "id",
    "title",
    "title_hu",
    "category",
    "min_age_months",
    "portions",
    "time_minutes",
    "ingredients",
    "method",
    "allergens",
    "verdict",
    "issues",
    "changes",
    "serve",
    "freezer",
}
TOPIC_GROUPS = [
    ("01-foundations.json", "Foundations"),
    ("02-practice.json", "At the table"),
    ("03-health.json", "Health and the short list"),
]
IMAGES = {
    "hero.jpg": "A bowl of smooth cooked food",
    "plate-a.jpg": "A plate of soft cooked foods",
    "plate-b.jpg": "A bowl of soft dairy food with fruit",
    "plate-c.jpg": "Soft baked pieces of food",
}


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def portions_label(value) -> str:
    text = str(value).strip()
    if text.isdigit():
        count = int(text)
        return "1 portion" if count == 1 else f"{count} portions"
    return text


def recipe_image(category: str) -> str:
    if category in {"simple-purees", "mixed-purees"}:
        return "hero.jpg"
    if category == "allergens":
        return "plate-b.jpg"
    if category in {"finger-foods", "snacks"}:
        return "plate-c.jpg"
    return "plate-a.jpg"


def added_word(text: str, word: str) -> bool:
    cleaned = text.lower()
    cleaned = re.sub(
        r"unsalted|unsweetened|no added salt|no added sugar|without salt|"
        r"without sugar|no salt|no sugar|no honey|sugar-free|salt-free",
        " ",
        cleaned,
    )
    return re.search(rf"\b{word}\b", cleaned) is not None


def validate(recipes: list[dict], topics: list[dict]) -> None:
    errors: list[str] = []
    seen: set[str] = set()
    topic_ids = {topic["id"] for topic in topics}
    if len(topic_ids) != len(topics):
        errors.append("Duplicate topic ids")
    for topic in topics:
        finding_ids = [item["id"] for item in topic["findings"]]
        section_ids = [item["id"] for item in topic["sections"]]
        if finding_ids != section_ids:
            errors.append(f"{topic['id']}: finding ids do not match section ids")
        for ref in topic["references"]:
            if not str(ref.get("url", "")).startswith("https://"):
                errors.append(f"{topic['id']}: reference missing https url ({ref.get('title')})")
    for recipe in recipes:
        missing = RECIPE_KEYS - set(recipe)
        if missing:
            errors.append(f"{recipe.get('id', '?')}: missing {sorted(missing)}")
            continue
        rid = recipe["id"]
        if rid in seen:
            errors.append(f"Duplicate recipe id {rid}")
        seen.add(rid)
        if not re.fullmatch(r"[a-z0-9-]+", rid):
            errors.append(f"{rid}: id must be lowercase kebab-case")
        if recipe["category"] not in CATEGORIES:
            errors.append(f"{rid}: unknown category {recipe['category']}")
        if recipe["verdict"] not in VERDICTS:
            errors.append(f"{rid}: unknown verdict {recipe['verdict']}")
        age = recipe["min_age_months"]
        if not isinstance(age, int) or age < 6 or age > 24:
            errors.append(f"{rid}: min_age_months must be an int from 6 to 24")
        if not isinstance(recipe["time_minutes"], int):
            errors.append(f"{rid}: time_minutes must be an int")
        if not isinstance(recipe["freezer"], bool):
            errors.append(f"{rid}: freezer must be a bool")
        if len(recipe["allergens"]) != len(set(recipe["allergens"])):
            errors.append(f"{rid}: duplicate allergens")
        unknown = set(recipe["allergens"]) - ALLERGENS
        if unknown:
            errors.append(f"{rid}: unknown allergens {sorted(unknown)}")
        if not (4 <= len(recipe["method"]) <= 8):
            errors.append(f"{rid}: method should have 4 to 8 steps, has {len(recipe['method'])}")
        blob = json.dumps(recipe, ensure_ascii=False)
        low = blob.lower()
        for banned in ("ambrus", "kérek", "kerek meg", "boook"):
            if banned in low:
                errors.append(f"{rid}: contains a book or publisher name")
        listed = " ".join(
            f"{item.get('amount', '')} {item.get('item', '')}" for item in recipe["ingredients"]
        )
        if added_word(listed, "honey") or "méz" in listed.lower():
            errors.append(f"{rid}: honey is not used in these recipes")
        if age < 12 and added_word(listed, "salt"):
            errors.append(f"{rid}: added salt under 12 months")
        if age < 12 and added_word(listed, "sugar"):
            errors.append(f"{rid}: added sugar under 12 months")
        listed_low = listed.lower()
        for bad in ("stock cube", "soy sauce", "worcester", "ham", "bacon", "chorizo", "feta", "mustard"):
            if bad in listed_low and age < 12:
                errors.append(f"{rid}: {bad} under 12 months")
    if len(recipes) < 100:
        errors.append(f"Expected a full recipe set, found {len(recipes)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        raise SystemExit(f"{len(errors)} content error(s)")


def as_prose(value) -> str:
    if isinstance(value, list):
        return " ".join(str(part).strip() for part in value if str(part).strip())
    return str(value).strip()


def normalize_recipe(recipe: dict) -> dict:
    for key in ("issues", "changes", "serve", "title", "title_hu", "portions"):
        if key in recipe:
            recipe[key] = as_prose(recipe[key])
    method = recipe.get("method")
    if isinstance(method, list):
        recipe["method"] = [as_prose(step) for step in method if as_prose(step)]
    if isinstance(recipe.get("min_age_months"), float) and recipe["min_age_months"].is_integer():
        recipe["min_age_months"] = int(recipe["min_age_months"])
    if isinstance(recipe.get("time_minutes"), float) and recipe["time_minutes"].is_integer():
        recipe["time_minutes"] = int(recipe["time_minutes"])
    return recipe


def load_content():
    topics: list[dict] = []
    groups: list[tuple[str, list[dict]]] = []
    for filename, label in TOPIC_GROUPS:
        batch = load_json(CONTENT / "topics" / filename)
        topics.extend(batch)
        groups.append((label, batch))
    recipes: list[dict] = []
    recipe_dir = CONTENT / "recipes"
    files = sorted(recipe_dir.glob("*.json"))
    if not files:
        raise SystemExit("No recipe JSON files in content/recipes")
    for path in files:
        batch = load_json(path)
        if not isinstance(batch, list):
            raise SystemExit(f"{path.name} must be a JSON array")
        recipes.extend(normalize_recipe(recipe) for recipe in batch)
    validate(recipes, topics)
    return groups, topics, recipes


def chrome(title: str, body: str, current: str = "") -> str:
    def link(href: str, label: str, key: str) -> str:
        mark = ' aria-current="page"' if current == key else ""
        return f'<a href="{href}"{mark}>{label}</a>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="Original evidence-checked notes and recipes for the first years of solid food. Inspired by a Hungarian weaning book. Not medical advice.">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560;9..144,640&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/site.css">
</head>
<body>
  <header class="wrap nav">
    <a class="brand" href="/">First foods</a>
    <nav class="nav-links">
      {link("/topics/", "Guides", "topics")}
      {link("/recipes/", "Recipes", "recipes")}
      {link("/about.html", "About", "about")}
    </nav>
  </header>
  <main class="wrap">
    {body}
  </main>
  <footer class="wrap footer">
    <p>Inspired by <em>Anya, kérek még!</em> (Ambrus Éva, BOOOK Kiadó). The words, recipes, and photographs on this site are original. This is not that book.</p>
    <p>This is general information, not personal medical advice. A health visitor or paediatrician knows your child. For a choking baby, use training from a first-aid course. In an emergency, call your local emergency number.</p>
  </footer>
</body>
</html>
"""


def write_page(relative: str, document: str) -> None:
    path = DIST / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8", newline="\n")


def home(groups, recipes) -> None:
    cards = []
    for _label, batch in groups:
        for topic in batch[:2]:
            cards.append(
                f"""<a class="card" href="/topics/{esc(topic['id'])}.html">
              <h2>{esc(topic['title'])}</h2>
              <p>{esc(topic['byline'])}</p>
            </a>"""
            )
    counts = {}
    for recipe in recipes:
        counts[recipe["verdict"]] = counts.get(recipe["verdict"], 0) + 1
    body = f"""
    <section class="hero">
      <div>
        <p class="kicker">Starting solids</p>
        <h1>Food for the first year, checked against the evidence.</h1>
        <p class="lede">Iron, allergens, salt, texture, and how a meal actually happens. Original recipes for the dishes families cook in a Hungarian kitchen, rewritten where the older versions added salt, sugar, honey, or a difficult texture.</p>
        <div class="actions">
          <a class="button" href="/topics/">Read the guides</a>
          <a class="button-ghost" href="/recipes/">Browse {len(recipes)} recipes</a>
        </div>
      </div>
      <figure class="hero-photo">
        <img src="/assets/img/hero.jpg" alt="{esc(IMAGES['hero.jpg'])}">
      </figure>
    </section>
    <section class="section">
      <div class="grid-3">
        <article class="card">
          <p class="kicker">Guides</p>
          <h2>Seventeen short topics</h2>
          <p>Each one opens with the findings, then the reasoning, then the papers and public pages those findings come from.</p>
        </article>
        <article class="card">
          <p class="kicker">Recipes</p>
          <h2>{counts.get('adjust', 0) + counts.get('replace', 0)} were changed</h2>
          <p>{counts.get('sound', 0)} ideas were already sound. The rest say, in plain language, what was wrong and what this version does instead.</p>
        </article>
        <article class="card">
          <p class="kicker">Limit</p>
          <h2>Not a clinic</h2>
          <p>Severe eczema or an existing egg allergy needs a clinician before peanut. Breathing trouble after a food is an emergency.</p>
        </article>
      </div>
    </section>
    <section class="section">
      <h2>Start here</h2>
      <div class="grid-2">
        {''.join(cards)}
      </div>
    </section>
    """
    write_page("index.html", chrome("First foods", body, "home"))


def about_page() -> None:
    body = """
    <section class="section">
      <p class="kicker">About</p>
      <h1>An original companion, not a copy of the book.</h1>
      <p class="lede">The dish ideas and the questions families ask came from <em>Anya, kérek még!</em> by Ambrus Éva, published by BOOOK Kiadó. The sentences on this site were written for it. The book’s text and photographs are not reproduced.</p>
    </section>
    <section class="section prose">
      <h2>What was kept</h2>
      <p>The shape of a Hungarian weaning kitchen: pumpkin, apple, cottage cheese, paprika without the heat, liver once in a while, fish without bones, egg, beans, and the small celebration cakes families actually want to bake. Where a dish was already a plain cooked fruit or vegetable, the recipe stays close to that idea.</p>
      <h2>What was changed</h2>
      <p>Added salt and sugar come out of food for children under one. Honey is not used at all here. Peanut, egg, milk, wheat, sesame, fish, soy, and ground nuts are offered around six months in a safe texture, instead of being delayed toward the first birthday. Fried crusts become oven bakes. Whole nuts, round hard pieces, carp, mustard in the early months, and salty ham are replaced. Each recipe page says whether the idea was sound, adjusted, or replaced.</p>
      <h2>How the guides were written</h2>
      <p>Claims about age, iron, protein, allergens, vitamin D, and choking are tied to a real source: ESPGHAN, WHO, EFSA, the LEAP and EAT trials, NHS, CDC, AAP, or a Hungarian public page. If a familiar local page still teaches an older fruit-then-meat ladder, the guide says so. This site does not invent a personal dose of medicine. Vitamin D for a breastfed baby is a prescribed product.</p>
      <h2>What this site will not do</h2>
      <p>It will not tell you that your child is well. It will not walk you through infant back blows as if reading them once were training. Take a first-aid course. If a baby is silent and cannot cough, call for emergency help.</p>
    </section>
    """
    write_page("about.html", chrome("About · First foods", body, "about"))


def topic_index(groups) -> None:
    blocks = []
    for label, batch in groups:
        cards = []
        for topic in batch:
            cards.append(
                f"""<a class="card" href="/topics/{esc(topic['id'])}.html">
              <h2>{esc(topic['title'])}</h2>
              <p>{esc(topic['byline'])}</p>
            </a>"""
            )
        blocks.append(f"<section class=\"section\"><h2>{esc(label)}</h2><div class=\"grid-2\">{''.join(cards)}</div></section>")
    body = f"""
    <section class="section">
      <p class="kicker">Guides</p>
      <h1>What to know before the recipes.</h1>
      <p class="lede">Short findings first. The longer explanation is on the same page, and the sources are linked.</p>
    </section>
    {''.join(blocks)}
    """
    write_page("topics/index.html", chrome("Guides · First foods", body, "topics"))


def topic_pages(groups) -> None:
    flat = [topic for _label, batch in groups for topic in batch]
    for topic in flat:
        side = []
        for other in flat:
            mark = ' aria-current="page"' if other["id"] == topic["id"] else ""
            side.append(f'<a href="/topics/{esc(other["id"])}.html"{mark}>{esc(other["title"])}</a>')
        findings = []
        for finding in topic["findings"]:
            findings.append(
                f"""<article class="finding">
              <a href="#{esc(finding['id'])}"><strong>{esc(finding['lead'])}</strong> {esc(finding['text'])}</a>
            </article>"""
            )
        sections = []
        for section in topic["sections"]:
            paragraphs = "".join(f"<p>{esc(p)}</p>" for p in section["paragraphs"])
            sections.append(f"<h2 id=\"{esc(section['id'])}\">{esc(section['heading'])}</h2>{paragraphs}")
        refs = []
        for index, ref in enumerate(topic["references"], start=1):
            refs.append(
                f"""<li class="ref" id="ref-{index}">
              <a href="{esc(ref['url'])}">{esc(ref['title'])}</a>
              <div class="meta">{esc(ref['source'])}, {esc(ref['year'])}</div>
            </li>"""
            )
        image = topic.get("image") or "plate-a.jpg"
        alt = topic.get("image_alt") or IMAGES.get(image, "A bowl of soft food")
        body = f"""
        <div class="layout">
          <aside class="side">
            <strong>Guides</strong>
            {''.join(side)}
          </aside>
          <article class="prose">
            <p class="kicker">Guide</p>
            <h1>{esc(topic['title'])}</h1>
            <p class="lede">{esc(topic['byline'])}</p>
            <figure class="hero-photo">
              <img src="/assets/img/{esc(image)}" alt="{esc(alt)}">
            </figure>
            <h2>Findings</h2>
            {''.join(findings)}
            {''.join(sections)}
            <h2>References</h2>
            <ol class="refs">{''.join(refs)}</ol>
          </article>
        </div>
        """
        write_page(f"topics/{topic['id']}.html", chrome(f"{topic['title']} · First foods", body, "topics"))


def recipe_card(recipe: dict) -> str:
    verdict = recipe["verdict"]
    pill = "sage" if verdict == "sound" else "warn"
    return f"""<a class="recipe-card" href="/recipes/{esc(recipe['id'])}.html" data-recipe-card>
      <div class="pills">
        <span class="pill">{esc(recipe['min_age_months'])} months+</span>
        <span class="pill {pill}">{esc(VERDICTS[verdict])}</span>
        <span class="pill quiet">{esc(CATEGORIES[recipe['category']])}</span>
      </div>
      <h3>{esc(recipe['title'])}</h3>
      <p class="hu">{esc(recipe['title_hu'])}</p>
      <p>{esc(recipe['time_minutes'])} min · {esc(portions_label(recipe['portions']))}</p>
    </a>"""


def recipe_index(recipes: list[dict]) -> None:
    chips = ['<button type="button" data-filter-cat="all" aria-pressed="true">All</button>']
    for key, label in CATEGORIES.items():
        chips.append(f'<button type="button" data-filter-cat="{esc(key)}" aria-pressed="false">{esc(label)}</button>')
    verdict_chips = ['<button type="button" data-filter-verdict="all" aria-pressed="true">Any note</button>']
    for key, label in VERDICTS.items():
        verdict_chips.append(
            f'<button type="button" data-filter-verdict="{esc(key)}" aria-pressed="false">{esc(label)}</button>'
        )
    slim = [
        {
            "id": recipe["id"],
            "title": recipe["title"],
            "title_hu": recipe["title_hu"],
            "category": recipe["category"],
            "category_label": CATEGORIES[recipe["category"]],
            "min_age_months": recipe["min_age_months"],
            "time_minutes": recipe["time_minutes"],
            "portions": portions_label(recipe["portions"]),
            "verdict": recipe["verdict"],
            "verdict_label": VERDICTS[recipe["verdict"]],
        }
        for recipe in recipes
    ]
    payload = json.dumps(slim, ensure_ascii=False).replace("<", "\\u003c")
    cards = "".join(recipe_card(recipe) for recipe in recipes)
    body = f"""
    <section class="section">
      <p class="kicker">Recipes</p>
      <h1>Cook these versions.</h1>
      <p class="lede">Filter by the age of the child. A recipe appears when its minimum age is at or below the age you choose. Hungarian names are kept so you can find the dish you had in mind.</p>
      <div class="filters">
        <input type="search" data-filter-q placeholder="Search by name" aria-label="Search recipes">
        <label class="meta" for="age">Show recipes a child this age can start</label>
        <select id="age" data-filter-age>
          <option value="">Any minimum age</option>
          <option value="6">6 months</option>
          <option value="7">7 months</option>
          <option value="8">8 months</option>
          <option value="9">9 months</option>
          <option value="10">10 months</option>
          <option value="12">12 months</option>
        </select>
        <div class="chips" role="group" aria-label="Category">{''.join(chips)}</div>
        <div class="chips" role="group" aria-label="Scrutiny">{''.join(verdict_chips)}</div>
        <p class="count" data-count>{len(recipes)} recipes</p>
      </div>
      <div class="recipe-list" data-recipe-list>
        {cards}
      </div>
    </section>
    <script>window.RECIPES = {payload};</script>
    <script src="/assets/site.js"></script>
    """
    write_page("recipes/index.html", chrome("Recipes · First foods", body, "recipes"))


def recipe_pages(recipes: list[dict]) -> None:
    by_category: dict[str, list[dict]] = {}
    for recipe in recipes:
        by_category.setdefault(recipe["category"], []).append(recipe)
    for recipe in recipes:
        image = recipe_image(recipe["category"])
        ingredients = "".join(
            f"<li><strong>{esc(item['amount'])}</strong> {esc(item['item'])}"
            + (f" <span class=\"meta\">({esc(item['note'])})</span>" if item.get("note") else "")
            + "</li>"
            for item in recipe["ingredients"]
        )
        steps = "".join(f"<li>{esc(step)}</li>" for step in recipe["method"])
        allergens = recipe["allergens"] or ["none"]
        allergen_pills = "".join(f'<span class="pill quiet">{esc(name)}</span>' for name in allergens)
        related = [other for other in by_category[recipe["category"]] if other["id"] != recipe["id"]][:3]
        related_html = "".join(
            f'<a href="/recipes/{esc(other["id"])}.html">{esc(other["title"])}</a>' for other in related
        )
        freezer = "Freezes well." if recipe["freezer"] else "Best eaten fresh."
        verdict = recipe["verdict"]
        body = f"""
        <article>
          <div class="recipe-hero">
            <div>
              <p class="kicker">{esc(CATEGORIES[recipe['category']])}</p>
              <h1>{esc(recipe['title'])}</h1>
              <p class="hu">{esc(recipe['title_hu'])}</p>
              <div class="pills">
                <span class="pill">{esc(recipe['min_age_months'])} months+</span>
                <span class="pill {'sage' if verdict == 'sound' else 'warn'}">{esc(VERDICTS[verdict])}</span>
                <span class="pill quiet">{esc(recipe['time_minutes'])} min</span>
                <span class="pill quiet">{esc(portions_label(recipe['portions']))}</span>
              </div>
              <p>{esc(recipe['serve'])}</p>
              <p class="meta">{freezer}</p>
            </div>
            <img src="/assets/img/{image}" alt="{esc(IMAGES[image])}">
          </div>
          <div class="split">
            <section class="panel">
              <h2>Ingredients</h2>
              <ul>{ingredients}</ul>
              <h2>Allergens</h2>
              <div class="pills">{allergen_pills}</div>
            </section>
            <section class="panel">
              <h2>Method</h2>
              <ol>{steps}</ol>
            </section>
          </div>
          <section class="callout {esc(verdict)}">
            <h2>{esc(VERDICTS[verdict])}</h2>
            <p>{esc(recipe['issues'])}</p>
            <p>{esc(recipe['changes'])}</p>
          </section>
          <aside class="side">
            <strong>More in this group</strong>
            {related_html or '<p class="meta">No other recipes in this group yet.</p>'}
          </aside>
        </article>
        """
        write_page(
            f"recipes/{recipe['id']}.html",
            chrome(f"{recipe['title']} · First foods", body, "recipes"),
        )


def copy_assets() -> None:
    target = DIST / "assets"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ASSETS, target)


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    groups, _topics, recipes = load_content()
    copy_assets()
    home(groups, recipes)
    about_page()
    topic_index(groups)
    topic_pages(groups)
    recipe_index(recipes)
    recipe_pages(recipes)
    print(f"Wrote {DIST} ({len(recipes)} recipes)")


if __name__ == "__main__":
    main()
