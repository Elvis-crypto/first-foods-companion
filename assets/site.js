(function () {
  var data = window.RECIPES || [];
  var list = document.querySelector("[data-recipe-list]");
  if (!list || !data.length) return;

  var query = document.querySelector("[data-filter-q]");
  var age = document.querySelector("[data-filter-age]");
  var count = document.querySelector("[data-count]");
  var category = "all";
  var verdict = "all";

  function pillClass(value) {
    return value === "sound" ? "pill sage" : "pill warn";
  }

  function text(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function card(recipe) {
    return (
      '<a class="recipe-card" href="/recipes/' + text(recipe.id) + '.html">' +
        '<div class="pills">' +
          '<span class="pill">' + text(recipe.min_age_months) + ' months+</span>' +
          '<span class="' + pillClass(recipe.verdict) + '">' + text(recipe.verdict_label) + '</span>' +
          '<span class="pill quiet">' + text(recipe.category_label) + '</span>' +
        '</div>' +
        '<h3>' + text(recipe.title) + '</h3>' +
        '<p class="hu">' + text(recipe.title_hu) + '</p>' +
        '<p>' + text(recipe.time_minutes) + ' min · ' + text(recipe.portions) + '</p>' +
      '</a>'
    );
  }

  function render() {
    var text = (query.value || "").trim().toLowerCase();
    var maxAge = age.value ? Number(age.value) : Infinity;
    var shown = data.filter(function (recipe) {
      if (category !== "all" && recipe.category !== category) return false;
      if (verdict !== "all" && recipe.verdict !== verdict) return false;
      if (recipe.min_age_months > maxAge) return false;
      if (!text) return true;
      var hay = (recipe.title + " " + recipe.title_hu + " " + recipe.category_label).toLowerCase();
      return hay.indexOf(text) !== -1;
    });
    list.innerHTML = shown.length
      ? shown.map(card).join("")
      : '<p class="meta">No recipes match those filters.</p>';
    if (count) count.textContent = shown.length + (shown.length === 1 ? " recipe" : " recipes");
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
  query.addEventListener("input", render);
  age.addEventListener("change", render);
})();
