#!/usr/bin/env python3
"""Generate the static First foods companion site from content JSON."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from html.parser import HTMLParser
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
    "allergens": "Allergen introduction",
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
    ("03-health.json", "Health and quick reference"),
]
IMAGES = {
    "hero.jpg": "A bowl of smooth pumpkin purée",
}
# Ingredient filters. Patterns run against the English ingredient line.
# Cheese is matched after cottage cheese so túró is not also listed as cheese.
FOODS = [
    ("apple", "Apple", "Alma", re.compile(r"(?<!pine)apple")),
    ("pear", "Pear", "Körte", re.compile(r"pear")),
    ("banana", "Banana", "Banán", re.compile(r"banana")),
    ("peach", "Peach", "Barack", re.compile(r"peach|apricot")),
    ("berries", "Berries", "Bogyós gyümölcs", re.compile(r"blueberr|strawberr|raspberr|blackberr|\bberr|\bcherr|\bplums?\b|pineapple|melon")),
    ("mango", "Mango", "Mangó", re.compile(r"mango")),
    ("avocado", "Avocado", "Avokádó", re.compile(r"avocado")),
    ("pumpkin", "Pumpkin", "Sütőtök", re.compile(r"pumpkin")),
    ("carrot", "Carrot", "Répa", re.compile(r"carrot")),
    ("sweet-potato", "Sweet potato", "Édesburgonya", re.compile(r"sweet potato")),
    ("potato", "Potato", "Burgonya", re.compile(r"(?<!sweet )potato")),
    ("zucchini", "Zucchini", "Cukkini", re.compile(r"zucchini|courgette")),
    ("broccoli", "Broccoli", "Brokkoli", re.compile(r"broccoli")),
    ("cauliflower", "Cauliflower", "Karfiol", re.compile(r"cauliflower")),
    ("spinach", "Spinach", "Spenót", re.compile(r"spinach")),
    ("peas", "Peas", "Borsó", re.compile(r"\bpeas?\b|green bean")),
    ("tomato", "Tomato", "Paradicsom", re.compile(r"tomato")),
    ("onion", "Onion or garlic", "Hagyma vagy fokhagyma", re.compile(r"onion|leek|garlic")),
    ("pepper", "Pepper", "Paprika", re.compile(r"\bpeppers?\b")),
    ("dairy", "Dairy", "Tejtermék", re.compile(r"yogurt|yoghurt|cottage cheese|\bcurd\b|(?<!cottage )cheese|mozzarella|(?<!breast )(?<!coconut )milk(?! path)(?! allergen)(?!-free)")),
    ("egg", "Egg", "Tojás", re.compile(r"\beggs?\b|egg yolk")),
    ("yogurt", "Yogurt", "Joghurt", re.compile(r"yogurt|yoghurt")),
    ("cottage", "Cottage cheese", "Túró", re.compile(r"cottage cheese|\bcurd\b")),
    ("cheese", "Cheese", "Sajt", re.compile(r"(?<!cottage )cheese|mozzarella")),
    ("milk", "Milk", "Tej", re.compile(r"(?<!breast )(?<!coconut )milk(?! path)(?! allergen)(?!-free)")),
    ("oats", "Oats", "Zab", re.compile(r"\boats?\b")),
    ("wheat", "Wheat", "Búza", re.compile(r"wheat|pasta|semolina|couscous|bulgur|breadcrumb|soft bread|(?<!chickpea )\bflour\b")),
    ("rice", "Rice", "Rizs", re.compile(r"\brice\b")),
    ("quinoa", "Quinoa", "Quinoa", re.compile(r"quinoa")),
    ("corn", "Corn", "Kukorica", re.compile(r"\bcorn\b|cornmeal|sweetcorn")),
    ("chicken", "Chicken", "Csirke", re.compile(r"chicken")),
    ("liver", "Liver", "Máj", re.compile(r"liver")),
    ("red-meat", "Beef, veal, or pork", "Marha, borjú vagy sertés", re.compile(r"beef|veal|pork")),
    ("fish", "Fish", "Hal", re.compile(r"salmon|cod|hake|trout|tuna|\bfish\b")),
    ("shrimp", "Shrimp", "Garnéla", re.compile(r"shrimp|prawn")),
    ("peanut", "Peanut", "Földimogyoró", re.compile(r"peanut")),
    ("tree-nut", "Tree nut", "Dióféle", re.compile(r"walnut|almond|chestnut")),
    ("sesame", "Sesame", "Szezám", re.compile(r"tahini|sesame")),
    ("legumes", "Beans, lentils, or tofu", "Bab, lencse vagy tofu", re.compile(r"lentil|chickpea|\bbeans?\b|tofu")),
]


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def recipe_image(recipe_id: str) -> str:
    return f"recipes/{recipe_id}.jpg"


def recipe_alt(ui, recipe: dict) -> str:
    name = recipe["title_hu"] if ui["code"] == "hu" else recipe["title"]
    return ui["photo_alt"].format(name=name)


def require_image(relative: str) -> None:
    path = ASSETS / "img" / relative
    if not path.is_file():
        raise SystemExit(f"Missing image {relative}")


def food_line(recipe: dict) -> str:
    """Ingredient text with refusals removed, so 'not peanut' does not count as peanut."""
    chunks = []
    for item in recipe["ingredients"]:
        chunks.append(f"{item.get('item', '')}. {item.get('note', '')}.")
    text = " ".join(chunks).lower()
    text = re.sub(r"\b[\w]+-free\b", " ", text)
    text = re.sub(r"\b(not|no|without|never)\b[^.;]*", " ", text)
    return text


def food_keys(recipe: dict) -> list[str]:
    text = food_line(recipe)
    items = " ".join(item.get("item", "") for item in recipe["ingredients"]).lower()
    found = []
    for key, _en, _hu, pattern in FOODS:
        # "The cheese" in a cottage-cheese note means the curd, not a second cheese.
        source = items if key == "cheese" else text
        if pattern.search(source):
            found.append(key)
    return found


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


SITE = "https://first-foods-companion.vercel.app"
AGES = (6, 7, 8, 9, 10, 12)

UI = {
    "en": {
        "code": "en",
        "prefix": "",
        "brand": "First foods",
        "guides": "Guides",
        "recipes": "Recipes",
        "about": "About",
        "language": "Language",
        "day": "Day",
        "night": "Night",
        "sign_in": "Sign in",
        "edit_text": "Edit text",
        "edit_done": "Done",
        "reset_page": "Reset this page",
        "reset_confirm": "Remove your edits on this page?",
        "edit_saved": "Saved",
        "edit_error": "Could not save that edit.",
        "edit_hint": "Your edits stay on your account. Other people still see the original.",
        "months": "months+",
        "empty": "No recipes match those filters.",
        "one": "recipe",
        "many": "recipes",
        "description": "Evidence-checked guides and original recipes for your baby’s first years of solid food. Inspired by a Hungarian weaning book. Not medical advice.",
        "footer1": "Inspired by <em>Anya, kérek még!</em> (Ambrus Éva, BOOOK Kiadó). All the text, recipes, and photos on this site are our own. This is not that book.",
        "footer2": "This is general information, not personal medical advice. Your health visitor or paediatrician knows your child. If a baby is choking, use what you learned on a first-aid course. In an emergency, call your local emergency number.",
        "groups": {
            "01-foundations.json": "Foundations",
            "02-practice.json": "At the table",
            "03-health.json": "Health and quick reference",
        },
        "categories": dict(CATEGORIES),
        "verdicts": dict(VERDICTS),
        "allergens": {
            "milk": "milk", "egg": "egg", "gluten": "gluten", "fish": "fish",
            "crustacean": "crustacean", "peanut": "peanut", "tree-nut": "tree nut",
            "sesame": "sesame", "soy": "soy", "mustard": "mustard", "celery": "celery",
            "sulphite": "sulphite", "none": "none",
        },
        "portion_one": "1 portion",
        "portion_many": "{n} portions",
        "freezer_yes": "Freezes well.",
        "freezer_no": "Best eaten fresh.",
        "kicker": "Starting solids",
        "h1": "Feeding your baby in the first year, checked against the evidence.",
        "lede": "Iron, allergens, salt, texture, and what mealtimes really look like. Original recipes for the dishes Hungarian families love to cook, reworked wherever the older versions called for salt, sugar, honey, or a tricky texture.",
        "read_guides": "Read the guides",
        "browse": "Browse {n} recipes",
        "card_guides_h": "Seventeen short topics",
        "card_guides_p": "Each one starts with the key points, then explains why, and links to the studies and official pages behind them.",
        "changed_h": "{n} recipes reworked",
        "changed_p": "{sound} ideas were fine as they were. For the rest, we explain in plain language what the problem was and what we do instead.",
        "limit_h": "Not a substitute for a doctor",
        "limit_p": "If your baby has severe eczema or a known egg allergy, see a doctor before introducing peanut. Breathing difficulty after eating is an emergency.",
        "start": "Start here",
        "about_kicker": "About",
        "about_h1": "An original companion, not a copy of the book.",
        "about_lede": "The dish ideas and the questions families ask came from <em>Anya, kérek még!</em> by Ambrus Éva, published by BOOOK Kiadó. Everything written here is new. The book’s text and photos are not reproduced.",
        "about_sections": [
            ("What was kept", "The feel of a Hungarian weaning kitchen: pumpkin, apple, cottage cheese, mild paprika, the occasional bit of liver, boneless fish, egg, beans, and the little party cakes families really want to bake. Where a dish was already a simple cooked fruit or vegetable, the recipe stays close to the original idea. The book’s view on allergens stays too: holding them back doesn’t prevent allergy, but they shouldn’t start before six months. So peanut, egg, milk, wheat, sesame, fish, soy, and ground nuts come in from around six months, in a texture that’s safe for the age."),
            ("What was changed", "No added salt or sugar for children under one. No honey anywhere. Fried coatings are baked in the oven instead. Whole nuts, hard round pieces, carp, mustard in the early months, and salty ham have been swapped out. Each recipe page tells you whether the idea was fine as it was, adjusted, or replaced."),
            ("How the guides were written", "Every claim about age, iron, protein, allergens, vitamin D, and choking is backed by a real source: ESPGHAN, WHO, EFSA, the LEAP and EAT trials, NHS, CDC, AAP, or an official Hungarian page. Where a familiar local page still teaches the old fruit-first, meat-later order, the guide points that out. This site never suggests a personal medicine dose: vitamin D for a breastfed baby is prescribed."),
            ("What this site will not do", "It can’t tell you whether your child is well. It won’t walk you through back blows as if reading about them once were enough training. Take a first-aid course. If a baby goes silent and can’t cough, call for emergency help."),
        ],
        "guides_h1": "What to know before the recipes.",
        "guides_lede": "The key points come first. The fuller explanation is on the same page, with links to the sources.",
        "findings": "Key points",
        "references": "References",
        "side_guides": "Guides",
        "cook_h1": "Recipes to cook.",
        "cook_lede": "Filter by your child’s age, or pick ingredients to include or leave out. Recipes that start at the age you choose come first. Ones suitable from earlier stay on the list too, since they’re still fine. We’ve kept the Hungarian names so you can find the dish you have in mind.",
        "ingredient_label": "Ingredients",
        "ingredient_find": "Find an ingredient",
        "ingredient_hint": "Click once to include it, twice to leave it out, and a third time to clear.",
        "ingredient_clear": "Clear ingredients",
        "food_required": ", included",
        "food_excluded": ", excluded",
        "search_placeholder": "Search by name or ingredient",
        "search_label": "Search recipes",
        "age_label": "Show recipes suitable from this age",
        "any_age": "Any age",
        "age_option": "{n} months",
        "age_starts": "Starts at {n} months",
        "age_earlier": "Also fine from earlier",
        "age_note": "New at {n} months: {start}. Suitable from earlier: {earlier}.",
        "age_note_only": "New at {n} months: {start}.",
        "age_note_earlier": "Nothing new at {n} months. Suitable from earlier: {earlier}.",
        "any_note": "Any",
        "all": "All",
        "category_label": "Category",
        "scrutiny_label": "Our verdict",
        "ingredients": "Ingredients",
        "allergens_h": "Allergens",
        "method": "Method",
        "more": "More like this",
        "more_empty": "No other recipes like this yet.",
        "doc_title": "First foods",
        "photo_alt": "A serving of {name}",
        "img_alt": dict(IMAGES),
    },
    "hu": {
        "code": "hu",
        "prefix": "/hu",
        "brand": "Első ételek",
        "guides": "Útmutatók",
        "recipes": "Receptek",
        "about": "Az oldalról",
        "language": "Nyelv",
        "day": "Nappal",
        "night": "Éjszaka",
        "sign_in": "Belépés",
        "edit_text": "Szöveg szerkesztése",
        "edit_done": "Kész",
        "reset_page": "Oldal visszaállítása",
        "reset_confirm": "Törlöd a saját módosításaidat ezen az oldalon?",
        "edit_saved": "Mentve",
        "edit_error": "A módosítást nem sikerült menteni.",
        "edit_hint": "A módosításaid a te fiókodhoz tartoznak. Mások az eredetit látják.",
        "months": "hónapos kortól",
        "empty": "Nincs a szűrésnek megfelelő recept.",
        "one": "recept",
        "many": "recept",
        "description": "Tudományosan ellenőrzött útmutatók és saját receptek a hozzátáplálás első éveihez. Egy magyar hozzátáplálós könyv ihlette. Nem orvosi tanács.",
        "footer1": "Az <em>Anya, kérek még!</em> (Ambrus Éva, BOOOK Kiadó) ihlette. Az oldalon minden szöveg, recept és fotó saját. Ez nem az a könyv.",
        "footer2": "Ez általános tájékoztatás, nem személyre szabott orvosi tanács. A gyerekedet a védőnő és a gyerekorvos ismeri. Ha a baba fullad, az elsősegély-tanfolyamon tanultakat alkalmazd. Vészhelyzetben hívd a segélyhívót.",
        "groups": {
            "01-foundations.json": "Alapok",
            "02-practice.json": "Az asztalnál",
            "03-health.json": "Egészség és puska",
        },
        "categories": {
            "simple-purees": "Egyszerű pürék",
            "mixed-purees": "Vegyes pürék",
            "finger-foods": "Puha falatok",
            "toddler-meals": "Ételek nagyobbaknak",
            "snacks": "Tízórai, uzsonna",
            "celebrations": "Ünnepi finomságok",
            "basics": "Alapok",
            "allergens": "Allergének bevezetése",
        },
        "verdicts": {"sound": "Eredetileg is jó", "adjust": "Átdolgozva", "replace": "Lecserélve"},
        "allergens": {
            "milk": "tej", "egg": "tojás", "gluten": "glutén", "fish": "hal",
            "crustacean": "rákféle", "peanut": "földimogyoró", "tree-nut": "dióféle",
            "sesame": "szezám", "soy": "szója", "mustard": "mustár", "celery": "zeller",
            "sulphite": "szulfit", "none": "nincs",
        },
        "portion_one": "1 adag",
        "portion_many": "{n} adag",
        "freezer_yes": "Jól fagyasztható.",
        "freezer_no": "Frissen a legjobb.",
        "kicker": "Hozzátáplálás",
        "h1": "Mit egyen a baba az első évben? Tudományosan ellenőrizve.",
        "lede": "Vas, allergének, só, állag, és hogy hogyan zajlik egy étkezés a valóságban. Saját receptek a magyar konyha kedvelt babaételeihez, átdolgozva ott, ahol a régi változat sót, cukrot, mézet vagy nehezen kezelhető állagot írt elő.",
        "read_guides": "Irány az útmutatók",
        "browse": "Böngéssz {n} recept között",
        "card_guides_h": "Tizenhét rövid téma",
        "card_guides_p": "Mindegyik a lényeggel kezdődik, utána jön a magyarázat, végül a tanulmányok és hivatalos oldalak, amelyekre épül.",
        "changed_h": "{n} receptet átdolgoztunk",
        "changed_p": "{sound} ötlet eleve rendben volt. A többinél egyszerűen elmondjuk, mi volt a gond, és mit csinálunk helyette.",
        "limit_h": "Nem helyettesíti az orvost",
        "limit_p": "Súlyos ekcéma vagy ismert tojásallergia esetén a földimogyoró bevezetése előtt beszélj orvossal. Ha evés után nehézzé válik a légzés, az vészhelyzet.",
        "start": "Kezdd itt",
        "about_kicker": "Az oldalról",
        "about_h1": "Önálló kísérőoldal, nem a könyv másolata.",
        "about_lede": "Az ételötleteket és a szülők gyakori kérdéseit Ambrus Éva <em>Anya, kérek még!</em> című könyve (BOOOK Kiadó) ihlette. Minden mondatot ehhez az oldalhoz írtunk, a könyv szövegét és fotóit nem közöljük.",
        "about_sections": [
            ("Ami megmaradt", "A magyar hozzátáplálós konyha jellege: sütőtök, alma, túró, édesnemes paprika, időnként máj, szálkátlan hal, tojás, bab, és azok a kis ünnepi sütik, amelyeket a családok tényleg szívesen sütnek. Ahol az étel eleve egyszerű főtt gyümölcs vagy zöldség volt, a recept az eredeti ötletnél marad. A könyv allergénekről vallott álláspontja is marad: a késleltetés nem előzi meg az allergiát, hat hónapos kor előtt viszont nem kezdjük el őket. A földimogyoró, a tojás, a tej, a búza, a szezám, a hal, a szója és a darált dióféle ezért hat hónapos kor körül kerül a tányérra, a korának megfelelő, biztonságos állagban."),
            ("Ami megváltozott", "Egyéves kor alatt nincs hozzáadott só és cukor. Mézet egyik recept sem használ. A bundázott, olajban sült ételek sütőben készülnek, és puhák maradnak. Az egész dió, a kemény, kerek falatok, a ponty, a korai mustár és a sós sonka helyett mást használunk. Minden receptoldalon ott áll, hogy az ötlet eleve jó volt, átdolgoztuk, vagy lecseréltük."),
            ("Hogyan készültek az útmutatók", "Az életkorra, a vasra, a fehérjére, az allergénekre, a D-vitaminra és a félrenyelésre vonatkozó minden állítás mögött valódi forrás áll: ESPGHAN, WHO, EFSA, a LEAP és az EAT vizsgálat, NHS, CDC, AAP vagy magyar szakmai összefoglaló. Ha egy ismert hazai oldal még a régi „előbb gyümölcs, aztán hús” sorrendet tanítja, az útmutató ezt jelzi. Az oldal soha nem ajánl személyre szabott gyógyszeradagot: a szoptatott baba D-vitaminját orvos írja fel."),
            ("Amit ez az oldal nem tesz meg", "Nem tudja megmondani, hogy a gyereked jól van-e. Nem pótolja a csecsemő-elsősegély tanfolyamot, ezért érdemes elvégezni egyet. Ha a baba elnémul, és nem tud köhögni, azonnal hívj segítséget."),
        ],
        "guides_h1": "Amit a receptek előtt érdemes tudni.",
        "guides_lede": "Elöl a lényeg röviden. A részletes magyarázat ugyanazon az oldalon olvasható, a forrásokat pedig belinkeltük.",
        "findings": "A lényeg",
        "references": "Források",
        "side_guides": "Útmutatók",
        "cook_h1": "Receptek a konyhába.",
        "cook_lede": "Szűrj a gyereked kora szerint, vagy jelöld be, milyen hozzávaló legyen benne, és mi maradjon ki. A választott kortól ajánlott receptek kerülnek előre, de a korábbiak is a listán maradnak, hiszen azok is adhatók. A megszokott ételneveket megtartottuk, hogy könnyen rátalálj arra, amit keresel.",
        "ingredient_label": "Hozzávalók",
        "ingredient_find": "Hozzávaló keresése",
        "ingredient_hint": "Egy kattintás: legyen benne. Kettő: maradjon ki. Három: törlés.",
        "ingredient_clear": "Hozzávalók törlése",
        "food_required": ", legyen benne",
        "food_excluded": ", maradjon ki",
        "search_placeholder": "Keresés név vagy hozzávaló szerint",
        "search_label": "Receptek keresése",
        "age_label": "Ettől a kortól adható receptek",
        "any_age": "Bármilyen kor",
        "age_option": "{n} hónapos",
        "age_starts": "{n} hónapos kortól",
        "age_earlier": "Korábban is adható",
        "age_note": "{n} hónapos kortól új: {start}. Korábbról is adható: {earlier}.",
        "age_note_only": "{n} hónapos kortól új: {start}.",
        "age_note_earlier": "{n} hónapos kortól nincs új recept. Korábbról is adható: {earlier}.",
        "any_note": "Bármelyik",
        "all": "Mind",
        "category_label": "Csoport",
        "scrutiny_label": "Értékelés",
        "ingredients": "Hozzávalók",
        "allergens_h": "Allergének",
        "method": "Elkészítés",
        "more": "Hasonló receptek",
        "more_empty": "Ebben a csoportban még nincs több recept.",
        "doc_title": "Első ételek",
        "photo_alt": "Tálalva: {name}",
        "img_alt": {
            "hero.jpg": "Egy tál sima sütőtökpüré",
        },
    },
}


def digits(value) -> list[str]:
    return re.findall(r"\d+", str(value))


def require_text(source: dict, key: str, label: str) -> str:
    value = source.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SystemExit(f"{label}: Hungarian field {key} is missing")
    return value.strip()


def guard_hungarian_recipe(recipe: dict) -> None:
    label = recipe["id"]
    listed = " ".join(
        f"{item.get('amount', '')} {item.get('item', '')}" for item in recipe["ingredients"]
    ).lower()
    if re.search(r"\b(honey|méz|mézet)\b", listed):
        raise SystemExit(f"{label}: honey in Hungarian ingredients")
    if recipe["min_age_months"] < 12:
        for word in ("só", "cukor", "cukrot", "sonka", "mustár", "szójaszósz", "leveskocka", "szalonna"):
            if re.search(rf"\b{word}\b", listed):
                raise SystemExit(f"{label}: {word} in Hungarian ingredients under 12 months")
    prose = " ".join(
        [recipe["issues"], recipe["changes"], recipe["serve"], *recipe["method"]]
    ).lower()
    if "peanut" in recipe["allergens"] and "ekcém" not in prose:
        raise SystemExit(f"{label}: Hungarian peanut recipe lost the eczema warning")
    for banned in ("ambrus", "kérek", "boook"):
        if banned in prose:
            raise SystemExit(f"{label}: Hungarian recipe names the book")


def overlay_recipe(english: dict, hungarian: dict) -> dict:
    merged = json.loads(json.dumps(english))
    label = english["id"]
    for key in ("issues", "changes", "serve"):
        merged[key] = require_text(hungarian, key, label)
    if not isinstance(hungarian.get("method"), list) or len(hungarian["method"]) != len(english["method"]):
        raise SystemExit(f"{label}: Hungarian method length does not match")
    merged["method"] = [str(step).strip() for step in hungarian["method"]]
    if any(not step for step in merged["method"]):
        raise SystemExit(f"{label}: empty Hungarian method step")
    if merged["method"] == english["method"] and merged["issues"] == english["issues"]:
        raise SystemExit(f"{label}: Hungarian text is still English")
    ingredients = hungarian.get("ingredients")
    if not isinstance(ingredients, list) or len(ingredients) != len(english["ingredients"]):
        raise SystemExit(f"{label}: Hungarian ingredient count does not match")
    merged_ingredients = []
    for original, translated in zip(english["ingredients"], ingredients):
        amount = str(translated.get("amount") or original["amount"])
        if digits(amount) != digits(original["amount"]):
            amount = original["amount"]
        item = str(translated.get("item") or "").strip()
        if not item:
            raise SystemExit(f"{label}: Hungarian ingredient name is missing")
        note = str(translated.get("note") or "").strip()
        merged_ingredients.append({"amount": amount, "item": item, "note": note})
    merged["ingredients"] = merged_ingredients
    guard_hungarian_recipe(merged)
    return merged


def overlay_topic(english: dict, hungarian: dict) -> dict:
    merged = json.loads(json.dumps(english))
    label = english["id"]
    for key in ("title", "byline", "image_alt"):
        merged[key] = require_text(hungarian, key, label)
    findings = {item["id"]: item for item in hungarian.get("findings", [])}
    for finding in merged["findings"]:
        source = findings.get(finding["id"])
        if not source:
            raise SystemExit(f"{label}: missing Hungarian finding {finding['id']}")
        finding["lead"] = require_text(source, "lead", label)
        finding["text"] = require_text(source, "text", label)
    sections = {item["id"]: item for item in hungarian.get("sections", [])}
    for section in merged["sections"]:
        source = sections.get(section["id"])
        if not source:
            raise SystemExit(f"{label}: missing Hungarian section {section['id']}")
        section["heading"] = require_text(source, "heading", label)
        paragraphs = source.get("paragraphs")
        if not isinstance(paragraphs, list) or len(paragraphs) != len(section["paragraphs"]):
            raise SystemExit(f"{label}: Hungarian paragraph count for {section['id']}")
        section["paragraphs"] = [str(paragraph).strip() for paragraph in paragraphs]
    references = hungarian.get("references")
    if not isinstance(references, list) or len(references) != len(merged["references"]):
        raise SystemExit(f"{label}: Hungarian reference count does not match")
    for original, translated in zip(merged["references"], references):
        original["title"] = require_text(translated, "title", label)
        original["source"] = require_text(translated, "source", label)
    return merged


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
    for recipe in recipes:
        recipe["foods"] = food_keys(recipe)
    return groups, topics, recipes


def page_path(ui, bare: str) -> str:
    if bare in {"", "/"}:
        relative = "index.html"
    else:
        relative = bare.lstrip("/")
        if relative.endswith("/"):
            relative += "index.html"
    prefix = ui["prefix"].strip("/")
    if prefix:
        return prefix + "/" + relative
    return relative


def href(ui, bare: str) -> str:
    if bare in {"", "/"}:
        return ui["prefix"] + "/" if ui["prefix"] else "/"
    return ui["prefix"] + bare


def absolute(ui, bare: str) -> str:
    return SITE + href(ui, bare)


def portions_label(value, ui) -> str:
    text = str(value).strip()
    if text.isdigit():
        count = int(text)
        if count == 1:
            return ui["portion_one"]
        return ui["portion_many"].format(n=count)
    return text


def chrome(ui, title: str, body: str, current: str, bare: str, extra_script: str = "") -> str:
    def link(path: str, label: str, key: str) -> str:
        mark = ' aria-current="page"' if current == key else ""
        return f'<a href="{href(ui, path)}"{mark}>{label}</a>'

    selected_en = " selected" if ui["code"] == "en" else ""
    selected_hu = " selected" if ui["code"] == "hu" else ""
    en_href = absolute(UI["en"], bare)
    hu_href = absolute(UI["hu"], bare)
    return f"""<!DOCTYPE html>
<html lang="{ui['code']}" data-prefix="{esc(ui['prefix'])}" data-months="{esc(ui['months'])}" data-empty="{esc(ui['empty'])}" data-one="{esc(ui['one'])}" data-many="{esc(ui['many'])}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(ui['description'])}">
  <link rel="alternate" hreflang="en" href="{esc(en_href)}">
  <link rel="alternate" hreflang="hu" href="{esc(hu_href)}">
  <script>
    (function () {{
      try {{
        var theme = localStorage.getItem("theme");
        if (theme !== "day" && theme !== "night") {{
          theme = window.matchMedia("(prefers-color-scheme: dark)").matches ? "night" : "day";
        }}
        document.documentElement.setAttribute("data-theme", theme);
      }} catch (error) {{}}
    }})();
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,560;9..144,640&family=Source+Sans+3:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/assets/site.css">
</head>
<body>
  <header class="wrap nav">
    <a class="brand" href="{href(ui, '/')}">{esc(ui['brand'])}</a>
    <div class="nav-end">
      <nav class="nav-links">
        {link('/topics/', ui['guides'], 'topics')}
        {link('/recipes/', ui['recipes'], 'recipes')}
        {link('/about.html', ui['about'], 'about')}
      </nav>
      <div class="nav-tools">
        <label class="visually-hidden" for="lang-{ui['code']}">{esc(ui['language'])}</label>
        <select id="lang-{ui['code']}" data-lang aria-label="{esc(ui['language'])}">
          <option value="en"{selected_en}>English</option>
          <option value="hu"{selected_hu}>Magyar</option>
        </select>
        <button type="button" class="theme-toggle" data-theme-toggle data-day="{esc(ui['day'])}" data-night="{esc(ui['night'])}" aria-pressed="false">{esc(ui['night'])}</button>
        <div id="account-slot" data-no-edit hidden data-sign-in="{esc(ui['sign_in'])}" data-label-edit="{esc(ui['edit_text'])}" data-done="{esc(ui['edit_done'])}" data-reset="{esc(ui['reset_page'])}" data-confirm="{esc(ui['reset_confirm'])}" data-saved="{esc(ui['edit_saved'])}" data-error="{esc(ui['edit_error'])}" data-hint="{esc(ui['edit_hint'])}"></div>
      </div>
    </div>
  </header>
  <main class="wrap">
    {body}
  </main>
  <footer class="wrap footer">
    <p>{ui['footer1']}</p>
    <p>{esc(ui['footer2'])}</p>
  </footer>
  {extra_script}
  <script src="/assets/site.js"></script>
  <script src="/assets/editor.js"></script>
</body>
</html>
"""


VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
    "param", "source", "track", "wbr",
}
EDITABLE_TAGS = {
    "a", "button", "h1", "h2", "h3", "p", "li", "label", "option", "span",
    "strong", "em", "figcaption", "summary", "small", "dt", "dd", "th", "td", "legend",
}
SKIP_TREE_TAGS = {"script", "style", "textarea"}


class _Node:
    def __init__(self, kind: str, tag: str = "", attrs: list | None = None, data: str = "") -> None:
        self.kind = kind
        self.tag = tag
        self.attrs = attrs or []
        self.data = data
        self.children: list[_Node] = []


class _TreeParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = _Node("root")
        self.stack = [self.root]

    def _add(self, node: _Node) -> _Node:
        self.stack[-1].children.append(node)
        return node

    def handle_decl(self, decl: str) -> None:
        self._add(_Node("decl", data=decl))

    def handle_comment(self, data: str) -> None:
        self._add(_Node("comment", data=data))

    def handle_data(self, data: str) -> None:
        self._add(_Node("text", data=data))

    def handle_entityref(self, name: str) -> None:
        self._add(_Node("text", data=f"&{name};"))

    def handle_charref(self, name: str) -> None:
        self._add(_Node("text", data=f"&#{name};"))

    def handle_starttag(self, tag: str, attrs: list) -> None:
        node = self._add(_Node("element", tag=tag, attrs=list(attrs)))
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list) -> None:
        self._add(_Node("element", tag=tag, attrs=list(attrs)))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return


def _has_attr(node: _Node, name: str) -> bool:
    return any(key == name for key, _value in node.attrs)


def _visible_text(node: _Node) -> str:
    if node.kind == "text":
        return node.data
    if node.kind != "element" or node.tag in SKIP_TREE_TAGS:
        return ""
    return "".join(_visible_text(child) for child in node.children)


def _stamp_node(node: _Node, ancestor_unit: bool, ancestor_skip: bool, counter: int) -> int:
    if node.kind == "root":
        for child in node.children:
            counter = _stamp_node(child, ancestor_unit, ancestor_skip, counter)
        return counter
    if node.kind != "element":
        return counter
    skip = (
        ancestor_skip
        or node.tag in SKIP_TREE_TAGS
        or _has_attr(node, "data-recipe-list")
        or _has_attr(node, "data-no-edit")
    )
    unit = ancestor_unit
    blocked = (
        skip
        or unit
        or _has_attr(node, "data-edit")
        or _has_attr(node, "data-count")
        or _has_attr(node, "data-age-note")
        or _has_attr(node, "data-theme-toggle")
    )
    if node.tag in EDITABLE_TAGS and not blocked and _visible_text(node).strip():
        node.attrs.append(("data-edit", f"t{counter}"))
        counter += 1
        unit = True
    elif _has_attr(node, "data-edit"):
        unit = True
    for child in node.children:
        counter = _stamp_node(child, unit, skip, counter)
    return counter


def _serialize(node: _Node) -> str:
    if node.kind == "root":
        return "".join(_serialize(child) for child in node.children)
    if node.kind == "text":
        return node.data
    if node.kind == "decl":
        return f"<!{node.data}>"
    if node.kind == "comment":
        return f"<!--{node.data}-->"
    rendered = []
    for name, value in node.attrs:
        if value is None:
            rendered.append(f" {name}")
        else:
            rendered.append(f' {name}="{esc(value)}"')
    attrs = "".join(rendered)
    if node.tag in VOID_TAGS:
        return f"<{node.tag}{attrs}>"
    inner = "".join(_serialize(child) for child in node.children)
    return f"<{node.tag}{attrs}>{inner}</{node.tag}>"


def stamp_document(document: str) -> str:
    parser = _TreeParser()
    parser.feed(document)
    parser.close()
    _stamp_node(parser.root, False, False, 0)
    return _serialize(parser.root)


def write_page(relative: str, document: str) -> None:
    try:
        stamped = stamp_document(document)
        if stamped.count("<html") == 1 and stamped.count("</html>") == 1:
            document = stamped
    except Exception:
        pass
    path = DIST / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8", newline="\n")


def home(ui, groups, recipes) -> None:
    cards = []
    for _label, batch in groups:
        for topic in batch[:2]:
            cards.append(
                f"""<a class="card" href="{href(ui, '/topics/' + topic['id'] + '.html')}">
              <h2>{esc(topic['title'])}</h2>
              <p>{esc(topic['byline'])}</p>
            </a>"""
            )
    counts = {}
    for recipe in recipes:
        counts[recipe["verdict"]] = counts.get(recipe["verdict"], 0) + 1
    changed = counts.get("adjust", 0) + counts.get("replace", 0)
    image_key = "hero.jpg"
    body = f"""
    <section class="hero">
      <div>
        <p class="kicker">{esc(ui['kicker'])}</p>
        <h1>{esc(ui['h1'])}</h1>
        <p class="lede">{esc(ui['lede'])}</p>
        <div class="actions">
          <a class="button" href="{href(ui, '/topics/')}">{esc(ui['read_guides'])}</a>
          <a class="button-ghost" href="{href(ui, '/recipes/')}">{esc(ui['browse'].format(n=len(recipes)))}</a>
        </div>
      </div>
      <figure class="hero-photo">
        <img src="/assets/img/{image_key}" alt="{esc(ui['img_alt'][image_key])}">
      </figure>
    </section>
    <section class="section">
      <div class="grid-3">
        <article class="card">
          <p class="kicker">{esc(ui['guides'])}</p>
          <h2>{esc(ui['card_guides_h'])}</h2>
          <p>{esc(ui['card_guides_p'])}</p>
        </article>
        <article class="card">
          <p class="kicker">{esc(ui['recipes'])}</p>
          <h2>{esc(ui['changed_h'].format(n=changed))}</h2>
          <p>{esc(ui['changed_p'].format(sound=counts.get('sound', 0)))}</p>
        </article>
        <article class="card">
          <p class="kicker">{esc(ui['about'])}</p>
          <h2>{esc(ui['limit_h'])}</h2>
          <p>{esc(ui['limit_p'])}</p>
        </article>
      </div>
    </section>
    <section class="section">
      <h2>{esc(ui['start'])}</h2>
      <div class="grid-2">
        {''.join(cards)}
      </div>
    </section>
    """
    write_page(page_path(ui, "/"), chrome(ui, ui["doc_title"], body, "home", "/"))


def about_page(ui) -> None:
    sections = "".join(
        f"<h2>{esc(heading)}</h2><p>{esc(paragraph)}</p>"
        for heading, paragraph in ui["about_sections"]
    )
    body = f"""
    <section class="section">
      <p class="kicker">{esc(ui['about_kicker'])}</p>
      <h1>{esc(ui['about_h1'])}</h1>
      <p class="lede">{ui['about_lede']}</p>
    </section>
    <section class="section prose">
      {sections}
    </section>
    """
    write_page(page_path(ui, "/about.html"), chrome(ui, f"{ui['about']} · {ui['doc_title']}", body, "about", "/about.html"))


def topic_index(ui, groups) -> None:
    blocks = []
    for label, batch in groups:
        cards = []
        for topic in batch:
            cards.append(
                f"""<a class="card" href="{href(ui, '/topics/' + topic['id'] + '.html')}">
              <h2>{esc(topic['title'])}</h2>
              <p>{esc(topic['byline'])}</p>
            </a>"""
            )
        blocks.append(f"<section class=\"section\"><h2>{esc(label)}</h2><div class=\"grid-2\">{''.join(cards)}</div></section>")
    body = f"""
    <section class="section">
      <p class="kicker">{esc(ui['guides'])}</p>
      <h1>{esc(ui['guides_h1'])}</h1>
      <p class="lede">{esc(ui['guides_lede'])}</p>
    </section>
    {''.join(blocks)}
    """
    write_page(page_path(ui, "/topics/"), chrome(ui, f"{ui['guides']} · {ui['doc_title']}", body, "topics", "/topics/"))


def topic_pages(ui, groups) -> None:
    flat = [topic for _label, batch in groups for topic in batch]
    for topic in flat:
        side = []
        for other in flat:
            mark = ' aria-current="page"' if other["id"] == topic["id"] else ""
            side.append(f'<a href="{href(ui, "/topics/" + other["id"] + ".html")}"{mark}>{esc(other["title"])}</a>')
        findings = []
        for finding in topic["findings"]:
            findings.append(
                f"""<article class="finding">
              <a href="#{esc(finding['id'])}"><strong>{esc(finding['lead'])}</strong> {esc(finding['text'])}</a>
            </article>"""
            )
        sections = []
        for section in topic["sections"]:
            paragraphs = "".join(f"<p>{esc(paragraph)}</p>" for paragraph in section["paragraphs"])
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
        require_image(image)
        alt = topic.get("image_alt") or IMAGES.get(image, "")
        bare = f"/topics/{topic['id']}.html"
        body = f"""
        <div class="layout">
          <aside class="side">
            <strong>{esc(ui['side_guides'])}</strong>
            {''.join(side)}
          </aside>
          <article class="prose">
            <p class="kicker">{esc(ui['guides'])}</p>
            <h1>{esc(topic['title'])}</h1>
            <p class="lede">{esc(topic['byline'])}</p>
            <figure class="hero-photo">
              <img src="/assets/img/{esc(image)}" alt="{esc(alt)}">
            </figure>
            <h2>{esc(ui['findings'])}</h2>
            {''.join(findings)}
            {''.join(sections)}
            <h2>{esc(ui['references'])}</h2>
            <ol class="refs">{''.join(refs)}</ol>
          </article>
        </div>
        """
        write_page(page_path(ui, bare), chrome(ui, f"{topic['title']} · {ui['doc_title']}", body, "topics", bare))


def recipe_card(ui, recipe: dict) -> str:
    verdict = recipe["verdict"]
    pill = "sage" if verdict == "sound" else "warn"
    primary = recipe["title_hu"] if ui["code"] == "hu" else recipe["title"]
    secondary = recipe["title"] if ui["code"] == "hu" else recipe["title_hu"]
    edit = recipe["id"]
    return f"""<a class="recipe-card" href="{href(ui, '/recipes/' + recipe['id'] + '.html')}">
      <div class="pills">
        <span class="pill" data-edit="recipe:{esc(edit)}:age">{esc(recipe['min_age_months'])} {esc(ui['months'])}</span>
        <span class="pill {pill}" data-edit="recipe:{esc(edit)}:verdict">{esc(ui['verdicts'][verdict])}</span>
        <span class="pill quiet" data-edit="recipe:{esc(edit)}:category">{esc(ui['categories'][recipe['category']])}</span>
      </div>
      <h3 data-edit="recipe:{esc(edit)}:title">{esc(primary)}</h3>
      <p class="hu" data-edit="recipe:{esc(edit)}:secondary">{esc(secondary)}</p>
      <p data-edit="recipe:{esc(edit)}:details">{esc(recipe['time_minutes'])} min · {esc(portions_label(recipe['portions'], ui))}</p>
    </a>"""


def recipe_index(ui, recipes: list[dict]) -> None:
    chips = [f'<button type="button" data-filter-cat="all" aria-pressed="true">{esc(ui["all"])}</button>']
    for key, label in ui["categories"].items():
        chips.append(f'<button type="button" data-filter-cat="{esc(key)}" aria-pressed="false">{esc(label)}</button>')
    verdict_chips = [f'<button type="button" data-filter-verdict="all" aria-pressed="true">{esc(ui["any_note"])}</button>']
    for key, label in ui["verdicts"].items():
        verdict_chips.append(
            f'<button type="button" data-filter-verdict="{esc(key)}" aria-pressed="false">{esc(label)}</button>'
        )
    ages = "".join(
        f'<option value="{age}">{esc(ui["age_option"].format(n=age))}</option>' for age in AGES
    )
    slim = []
    for recipe in recipes:
        primary = recipe["title_hu"] if ui["code"] == "hu" else recipe["title"]
        secondary = recipe["title"] if ui["code"] == "hu" else recipe["title_hu"]
        slim.append({
            "id": recipe["id"],
            "title": recipe["title"],
            "title_hu": recipe["title_hu"],
            "primary": primary,
            "secondary": secondary,
            "category": recipe["category"],
            "category_label": ui["categories"][recipe["category"]],
            "min_age_months": recipe["min_age_months"],
            "time_minutes": recipe["time_minutes"],
            "portions": portions_label(recipe["portions"], ui),
            "verdict": recipe["verdict"],
            "verdict_label": ui["verdicts"][recipe["verdict"]],
            "foods": recipe.get("foods") or [],
            "ingredient_text": " ".join(item["item"] for item in recipe["ingredients"]),
        })
    used = {key for recipe in recipes for key in recipe.get("foods") or []}
    food_buttons = []
    for key, english, hungarian, _pattern in FOODS:
        if key not in used:
            continue
        label = english if ui["code"] == "en" else hungarian
        food_buttons.append(
            f'<button type="button" data-food="{esc(key)}" data-label="{esc(label)}" '
            f'data-state="off" aria-pressed="false">{esc(label)}</button>'
        )
    payload = json.dumps(slim, ensure_ascii=False).replace("<", "\\u003c")
    cards = "".join(recipe_card(ui, recipe) for recipe in recipes)
    body = f"""
    <section class="section">
      <p class="kicker">{esc(ui['recipes'])}</p>
      <h1>{esc(ui['cook_h1'])}</h1>
      <p class="lede">{esc(ui['cook_lede'])}</p>
      <div class="filters">
        <input type="search" data-filter-q placeholder="{esc(ui['search_placeholder'])}" aria-label="{esc(ui['search_label'])}">
        <label class="meta" for="age-{ui['code']}">{esc(ui['age_label'])}</label>
        <select id="age-{ui['code']}" data-filter-age>
          <option value="">{esc(ui['any_age'])}</option>
          {ages}
        </select>
        <p class="meta age-note" data-age-note hidden aria-live="polite" data-starts="{esc(ui['age_starts'])}" data-earlier="{esc(ui['age_earlier'])}" data-note="{esc(ui['age_note'])}" data-note-only="{esc(ui['age_note_only'])}" data-note-earlier="{esc(ui['age_note_earlier'])}"></p>
        <div class="chips" role="group" aria-label="{esc(ui['category_label'])}">{''.join(chips)}</div>
        <div class="chips" role="group" aria-label="{esc(ui['scrutiny_label'])}">{''.join(verdict_chips)}</div>
        <div class="food-filters">
          <label class="meta" for="food-{ui['code']}">{esc(ui['ingredient_label'])}</label>
          <input id="food-{ui['code']}" type="search" data-filter-foods placeholder="{esc(ui['ingredient_find'])}" aria-label="{esc(ui['ingredient_find'])}" autocomplete="off">
          <p class="meta">{esc(ui['ingredient_hint'])}</p>
          <div class="chips" role="group" aria-label="{esc(ui['ingredient_label'])}" data-food-chips data-required-suffix="{esc(ui['food_required'])}" data-excluded-suffix="{esc(ui['food_excluded'])}">{''.join(food_buttons)}</div>
          <button type="button" class="text-button" data-food-clear hidden>{esc(ui['ingredient_clear'])}</button>
        </div>
        <p class="count" data-count>{len(recipes)} {esc(ui['many'])}</p>
      </div>
      <div class="recipe-list" data-recipe-list>
        {cards}
      </div>
    </section>
    <script>window.RECIPES = {payload};</script>
    """
    write_page(
        page_path(ui, "/recipes/"),
        chrome(ui, f"{ui['recipes']} · {ui['doc_title']}", body, "recipes", "/recipes/", extra_script=""),
    )
    # The recipe payload must sit before site.js. chrome already appends site.js after extra_script,
    # and the payload is inside body, which is before that script. Good.


def recipe_pages(ui, recipes: list[dict]) -> None:
    by_category: dict[str, list[dict]] = {}
    for recipe in recipes:
        by_category.setdefault(recipe["category"], []).append(recipe)
    for recipe in recipes:
        image = recipe_image(recipe["id"])
        require_image(image)
        ingredients = "".join(
            f"<li><strong>{esc(item['amount'])}</strong> {esc(item['item'])}"
            + (f" <span class=\"meta\">({esc(item['note'])})</span>" if item.get("note") else "")
            + "</li>"
            for item in recipe["ingredients"]
        )
        steps = "".join(f"<li>{esc(step)}</li>" for step in recipe["method"])
        names = [ui["allergens"].get(name, name) for name in (recipe["allergens"] or ["none"])]
        allergen_pills = "".join(f'<span class="pill quiet">{esc(name)}</span>' for name in names)
        related = [other for other in by_category[recipe["category"]] if other["id"] != recipe["id"]][:3]
        related_html = "".join(
            f'<a href="{href(ui, "/recipes/" + other["id"] + ".html")}">{esc(other["title_hu"] if ui["code"] == "hu" else other["title"])}</a>'
            for other in related
        )
        freezer = ui["freezer_yes"] if recipe["freezer"] else ui["freezer_no"]
        verdict = recipe["verdict"]
        primary = recipe["title_hu"] if ui["code"] == "hu" else recipe["title"]
        secondary = recipe["title"] if ui["code"] == "hu" else recipe["title_hu"]
        bare = f"/recipes/{recipe['id']}.html"
        body = f"""
        <article>
          <div class="recipe-hero">
            <div>
              <p class="kicker">{esc(ui['categories'][recipe['category']])}</p>
              <h1>{esc(primary)}</h1>
              <p class="hu">{esc(secondary)}</p>
              <div class="pills">
                <span class="pill">{esc(recipe['min_age_months'])} {esc(ui['months'])}</span>
                <span class="pill {'sage' if verdict == 'sound' else 'warn'}">{esc(ui['verdicts'][verdict])}</span>
                <span class="pill quiet">{esc(recipe['time_minutes'])} min</span>
                <span class="pill quiet">{esc(portions_label(recipe['portions'], ui))}</span>
              </div>
              <p>{esc(recipe['serve'])}</p>
              <p class="meta">{esc(freezer)}</p>
            </div>
            <img src="/assets/img/{image}" alt="{esc(recipe_alt(ui, recipe))}">
          </div>
          <div class="split">
            <section class="panel">
              <h2>{esc(ui['ingredients'])}</h2>
              <ul>{ingredients}</ul>
              <h2>{esc(ui['allergens_h'])}</h2>
              <div class="pills">{allergen_pills}</div>
            </section>
            <section class="panel">
              <h2>{esc(ui['method'])}</h2>
              <ol>{steps}</ol>
            </section>
          </div>
          <section class="callout {esc(verdict)}">
            <h2>{esc(ui['verdicts'][verdict])}</h2>
            <p>{esc(recipe['issues'])}</p>
            <p>{esc(recipe['changes'])}</p>
          </section>
          <aside class="side">
            <strong>{esc(ui['more'])}</strong>
            {related_html or '<p class="meta">' + esc(ui['more_empty']) + '</p>'}
          </aside>
        </article>
        """
        write_page(page_path(ui, bare), chrome(ui, f"{primary} · {ui['doc_title']}", body, "recipes", bare))


def with_language(groups, recipes, lang: str):
    ui = UI[lang]
    labeled = []
    if lang == "en":
        for (filename, _label), batch in zip(TOPIC_GROUPS, [group[1] for group in groups]):
            labeled.append((ui["groups"][filename], batch))
        return ui, labeled, recipes
    hu_topics = {}
    for filename, _label in TOPIC_GROUPS:
        path = CONTENT / "hu" / "topics" / filename
        if not path.exists():
            raise SystemExit(f"Missing {path}")
        for topic in load_json(path):
            hu_topics[topic["id"]] = topic
    missing_topics = [
        topic["id"] for _label, batch in groups for topic in batch if topic["id"] not in hu_topics
    ]
    if missing_topics:
        raise SystemExit("Missing Hungarian topics: " + ", ".join(missing_topics))
    labeled = []
    for (filename, _label), batch in zip(TOPIC_GROUPS, [group[1] for group in groups]):
        labeled.append((ui["groups"][filename], [overlay_topic(topic, hu_topics[topic["id"]]) for topic in batch]))
    hu_recipes = {}
    for path in sorted((CONTENT / "hu" / "recipes").glob("*.json")):
        for recipe in load_json(path):
            recipe = normalize_recipe(recipe)
            hu_recipes[recipe["id"]] = recipe
    missing = [recipe["id"] for recipe in recipes if recipe["id"] not in hu_recipes]
    if missing:
        raise SystemExit("Missing Hungarian recipes: " + ", ".join(missing[:12]))
    translated = [overlay_recipe(recipe, hu_recipes[recipe["id"]]) for recipe in recipes]
    return ui, labeled, translated


def copy_assets() -> None:
    target = DIST / "assets"
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(ASSETS, target)


def render(lang: str, groups, recipes) -> None:
    ui, localized_groups, localized_recipes = with_language(groups, recipes, lang)
    home(ui, localized_groups, localized_recipes)
    about_page(ui)
    topic_index(ui, localized_groups)
    topic_pages(ui, localized_groups)
    recipe_index(ui, localized_recipes)
    recipe_pages(ui, localized_recipes)


def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    groups, _topics, recipes = load_content()
    copy_assets()
    render("en", groups, recipes)
    render("hu", groups, recipes)
    print(f"Wrote {DIST} ({len(recipes)} recipes, two languages)")


if __name__ == "__main__":
    main()
