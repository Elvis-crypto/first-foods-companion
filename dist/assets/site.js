(function () {
  var root = document.documentElement;
  var toggle = document.querySelector("[data-theme-toggle]");
  if (toggle) {
    function apply(theme) {
      root.setAttribute("data-theme", theme);
      var night = theme === "night";
      toggle.setAttribute("aria-pressed", night ? "true" : "false");
      toggle.textContent = night ? toggle.getAttribute("data-day") : toggle.getAttribute("data-night");
    }
    apply(root.getAttribute("data-theme") === "night" ? "night" : "day");
    toggle.addEventListener("click", function () {
      var next = root.getAttribute("data-theme") === "night" ? "day" : "night";
      try { localStorage.setItem("theme", next); } catch (error) {}
      apply(next);
    });
  }

  var lang = document.querySelector("[data-lang]");
  if (lang) {
    lang.addEventListener("change", function () {
      var choice = lang.value === "hu" ? "hu" : "en";
      var secure = location.protocol === "https:" ? "; Secure" : "";
      document.cookie = "lang=" + choice + "; Path=/; Max-Age=31536000; SameSite=Lax" + secure;
      var path = location.pathname;
      var onHu = path === "/hu" || path.indexOf("/hu/") === 0;
      var bare = onHu ? path.slice(3) || "/" : path;
      var next = choice === "hu" ? (bare === "/" ? "/hu/" : "/hu" + bare) : bare;
      if (next !== path) location.href = next;
    });
  }
})();

(function () {
  var data = window.RECIPES || [];
  var list = document.querySelector("[data-recipe-list]");
  if (!list || !data.length) return;

  var root = document.documentElement;
  var prefix = root.getAttribute("data-prefix") || "";
  var months = root.getAttribute("data-months") || "months+";
  var empty = root.getAttribute("data-empty") || "No recipes match those filters.";
  var one = root.getAttribute("data-one") || "recipe";
  var many = root.getAttribute("data-many") || "recipes";
  var query = document.querySelector("[data-filter-q]");
  var age = document.querySelector("[data-filter-age]");
  var ageNote = document.querySelector("[data-age-note]");
  var count = document.querySelector("[data-count]");
  var foodQuery = document.querySelector("[data-filter-foods]");
  var foodChips = document.querySelector("[data-food-chips]");
  var clearFoods = document.querySelector("[data-food-clear]");
  var category = "all";
  var verdict = "all";
  var include = Object.create(null);
  var exclude = Object.create(null);

  function escapeText(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function card(recipe) {
    var primary = recipe.primary || recipe.title;
    var secondary = recipe.secondary || recipe.title_hu;
    return (
      '<a class="recipe-card" href="' + prefix + "/recipes/" + escapeText(recipe.id) + '.html">' +
        '<div class="pills">' +
          '<span class="pill">' + escapeText(recipe.min_age_months) + " " + escapeText(months) + "</span>" +
          '<span class="' + (recipe.verdict === "sound" ? "pill sage" : "pill warn") + '">' + escapeText(recipe.verdict_label) + "</span>" +
          '<span class="pill quiet">' + escapeText(recipe.category_label) + "</span>" +
        "</div>" +
        "<h3>" + escapeText(primary) + "</h3>" +
        '<p class="hu">' + escapeText(secondary) + "</p>" +
        "<p>" + escapeText(recipe.time_minutes) + " min · " + escapeText(recipe.portions) + "</p>" +
      "</a>"
    );
  }

  function fillAge(template, values) {
    return String(template)
      .replace(/\{n\}/g, values.n)
      .replace(/\{start\}/g, values.start)
      .replace(/\{earlier\}/g, values.earlier);
  }

  function render(options) {
    var needle = query ? String(query.value || "").trim().toLowerCase() : "";
    var maxAge = age && age.value ? Number(age.value) : Infinity;
    if (!isFinite(maxAge)) maxAge = Infinity;
    var shown = data.filter(function (recipe) {
      if (category !== "all" && recipe.category !== category) return false;
      if (verdict !== "all" && recipe.verdict !== verdict) return false;
      if (Number(recipe.min_age_months) > maxAge) return false;
      var foods = recipe.foods || [];
      var key;
      for (key in include) {
        if (include[key] && foods.indexOf(key) === -1) return false;
      }
      for (key in exclude) {
        if (exclude[key] && foods.indexOf(key) !== -1) return false;
      }
      if (!needle) return true;
      var hay = [recipe.title, recipe.title_hu, recipe.primary, recipe.secondary, recipe.category_label, recipe.ingredient_text].join(" ").toLowerCase();
      return hay.indexOf(needle) !== -1;
    });
    var exact = [];
    var earlier = [];
    if (maxAge !== Infinity) {
      shown.forEach(function (recipe) {
        if (Number(recipe.min_age_months) === maxAge) exact.push(recipe);
        else earlier.push(recipe);
      });
    }
    var html = "";
    if (!shown.length) {
      html = '<p class="meta">' + escapeText(empty) + "</p>";
    } else if (maxAge === Infinity) {
      html = shown.map(card).join("");
    } else {
      var startsLabel = ageNote ? ageNote.getAttribute("data-starts") || "Starts at {n} months" : "Starts at {n} months";
      var earlierLabel = ageNote ? ageNote.getAttribute("data-earlier") || "Also fine from earlier" : "Also fine from earlier";
      var values = { n: String(maxAge), start: String(exact.length), earlier: String(earlier.length) };
      if (exact.length) {
        html += '<h2 class="age-group">' + escapeText(fillAge(startsLabel, values)) + "</h2>" + exact.map(card).join("");
      }
      if (earlier.length) {
        html += '<h2 class="age-group">' + escapeText(fillAge(earlierLabel, values)) + "</h2>" + earlier.map(card).join("");
      }
    }
    list.innerHTML = html;
    if (count) count.textContent = shown.length + " " + (shown.length === 1 ? one : many);
    if (ageNote) {
      if (maxAge === Infinity || !shown.length) {
        ageNote.hidden = true;
        ageNote.textContent = "";
      } else {
        var noteValues = { n: String(maxAge), start: String(exact.length), earlier: String(earlier.length) };
        var noteKey = exact.length && earlier.length ? "data-note" : exact.length ? "data-note-only" : "data-note-earlier";
        var noteFallback = exact.length && earlier.length
          ? "Starting at {n} months: {start}. Still fine from earlier: {earlier}."
          : exact.length
            ? "Starting at {n} months: {start}."
            : "Nothing starts at {n} months. Still fine from earlier: {earlier}.";
        ageNote.hidden = false;
        ageNote.textContent = fillAge(ageNote.getAttribute(noteKey) || noteFallback, noteValues);
      }
    }
    if (options && options.reveal) {
      var top = list.getBoundingClientRect().top;
      if (top > window.innerHeight - 120) list.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  function press(buttons, attr, value) {
    buttons.forEach(function (button) {
      button.setAttribute("aria-pressed", button.getAttribute(attr) === value ? "true" : "false");
    });
  }

  var categoryButtons = Array.prototype.slice.call(document.querySelectorAll("[data-filter-cat]"));
  var verdictButtons = Array.prototype.slice.call(document.querySelectorAll("[data-filter-verdict]"));
  categoryButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      category = button.getAttribute("data-filter-cat");
      press(categoryButtons, "data-filter-cat", category);
      render();
    });
  });
  verdictButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      verdict = button.getAttribute("data-filter-verdict");
      press(verdictButtons, "data-filter-verdict", verdict);
      render();
    });
  });
  if (query) query.addEventListener("input", render);
  if (age) age.addEventListener("change", function () { render({ reveal: true }); });

  var foodButtons = foodChips
    ? Array.prototype.slice.call(foodChips.querySelectorAll("[data-food]"))
    : [];
  var requiredSuffix = foodChips ? foodChips.getAttribute("data-required-suffix") || ", required" : ", required";
  var excludedSuffix = foodChips ? foodChips.getAttribute("data-excluded-suffix") || ", excluded" : ", excluded";

  function foodSelected() {
    var key;
    for (key in include) if (include[key]) return true;
    for (key in exclude) if (exclude[key]) return true;
    return false;
  }

  function syncFoodButtons() {
    var needle = foodQuery ? (foodQuery.value || "").trim().toLowerCase() : "";
    foodButtons.forEach(function (button) {
      var key = button.getAttribute("data-food");
      var state = include[key] ? "include" : exclude[key] ? "exclude" : "off";
      var name = button.getAttribute("data-label") || button.textContent;
      button.setAttribute("data-state", state);
      button.setAttribute("aria-pressed", state === "off" ? "false" : "true");
      button.setAttribute("aria-label", name + (state === "include" ? requiredSuffix : state === "exclude" ? excludedSuffix : ""));
      var visible = !needle || name.toLowerCase().indexOf(needle) !== -1 || state !== "off";
      button.hidden = !visible;
    });
    if (clearFoods) clearFoods.hidden = !foodSelected();
  }

  foodButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      var key = button.getAttribute("data-food");
      var state = button.getAttribute("data-state");
      if (state === "off") {
        include[key] = true;
        delete exclude[key];
      } else if (state === "include") {
        delete include[key];
        exclude[key] = true;
      } else {
        delete include[key];
        delete exclude[key];
      }
      syncFoodButtons();
      render();
    });
  });
  if (foodQuery) foodQuery.addEventListener("input", syncFoodButtons);
  if (clearFoods) {
    clearFoods.addEventListener("click", function () {
      include = Object.create(null);
      exclude = Object.create(null);
      syncFoodButtons();
      render();
    });
  }
  syncFoodButtons();
})();
