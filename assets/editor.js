(function () {
  var slot = document.getElementById("account-slot");
  if (!slot) return;

  var edits = Object.create(null);
  var editing = false;
  var signedIn = false;
  var ready = false;

  document.addEventListener("recipes:rendered", function () {
    applyEdits();
    if (editing) markEditable(true);
  });

  document.addEventListener("click", function (event) {
    if (!editing) return;
    var control = event.target.closest && event.target.closest("a, button");
    if (!control) return;
    if (control.closest("[data-no-edit]")) return;
    if (control.hasAttribute("data-theme-toggle")) return;
    event.preventDefault();
  }, true);

  document.addEventListener("focusout", function (event) {
    if (!editing) return;
    var el = event.target;
    if (!el || !el.getAttribute || !el.getAttribute("data-edit")) return;
    saveUnit(el);
  });

  document.addEventListener("paste", function (event) {
    if (!editing) return;
    var el = event.target.closest && event.target.closest("[data-edit]");
    if (!el) return;
    var data = event.clipboardData || window.clipboardData;
    if (!data) return;
    var text = data.getData("text/plain");
    if (text == null) return;
    event.preventDefault();
    var selection = window.getSelection();
    if (!selection || !selection.rangeCount) return;
    selection.deleteFromDocument();
    selection.getRangeAt(0).insertNode(document.createTextNode(text));
    selection.collapseToEnd();
  });

  function attr(name) {
    return slot.getAttribute(name) || "";
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function pagePath() {
    var path = location.pathname || "/";
    if (path.length > 180 || path.indexOf("..") !== -1) return "/";
    if (path.slice(-11) === "/index.html") path = path.slice(0, -10);
    if (!path) path = "/";
    return path;
  }

  function units() {
    return Array.prototype.slice.call(document.querySelectorAll("[data-edit]"));
  }

  function setStatus(message) {
    var status = slot.querySelector("[data-edit-status]");
    if (status) status.textContent = message || "";
  }

  function applyEdits() {
    units().forEach(function (el) {
      var key = el.getAttribute("data-edit");
      if (!key) return;
      if (!el.hasAttribute("data-original")) el.setAttribute("data-original", el.textContent);
      var next = Object.prototype.hasOwnProperty.call(edits, key) ? edits[key] : el.getAttribute("data-original");
      if (el.textContent !== next) el.textContent = next;
    });
  }

  function markEditable(on) {
    units().forEach(function (el) {
      if (on) {
        if (!el.hasAttribute("data-original")) el.setAttribute("data-original", el.textContent);
        el.setAttribute("contenteditable", "plaintext-only");
        el.setAttribute("spellcheck", "true");
      } else {
        el.removeAttribute("contenteditable");
        el.removeAttribute("spellcheck");
      }
    });
  }

  function clearPersonalText() {
    editing = false;
    edits = Object.create(null);
    units().forEach(function (el) {
      el.removeAttribute("contenteditable");
      if (el.hasAttribute("data-original")) el.textContent = el.getAttribute("data-original");
    });
  }

  function api(method, payload) {
    return window.Clerk.session.getToken().then(function (token) {
      if (!token) throw new Error("auth");
      var url = "/api/edits";
      var options = {
        method: method,
        headers: {
          Authorization: "Bearer " + token,
          "Content-Type": "application/json",
          Accept: "application/json"
        }
      };
      if (method === "GET") url += "?path=" + encodeURIComponent(pagePath());
      else options.body = JSON.stringify(payload);
      return fetch(url, options).then(function (res) {
        if (!res.ok) throw new Error("http");
        return res.json();
      });
    });
  }

  function loadEdits() {
    return api("GET").then(function (data) {
      var incoming = data && data.edits ? data.edits : {};
      var next = Object.create(null);
      Object.keys(incoming).forEach(function (key) {
        if (typeof incoming[key] === "string") next[key] = incoming[key];
      });
      edits = next;
      applyEdits();
      if (editing) markEditable(true);
      ready = true;
    });
  }

  function saveUnit(el) {
    var key = el.getAttribute("data-edit");
    if (!key || !ready) return;
    var body = el.textContent;
    var original = el.getAttribute("data-original") || "";
    if (body.length > 8000) {
      el.textContent = Object.prototype.hasOwnProperty.call(edits, key) ? edits[key] : original;
      setStatus(attr("data-error"));
      return;
    }
    var had = Object.prototype.hasOwnProperty.call(edits, key);
    var previous = had ? edits[key] : null;
    if (body === original && !had) return;
    var method = body === original ? "DELETE" : "PUT";
    var payload = body === original ? { path: pagePath(), key: key } : { path: pagePath(), key: key, body: body };
    api(method, payload).then(function () {
      if (method === "DELETE") delete edits[key];
      else edits[key] = body;
      setStatus(attr("data-saved"));
    }).catch(function () {
      if (had) edits[key] = previous;
      el.textContent = had ? previous : original;
      setStatus(attr("data-error"));
    });
  }

  function renderSignedOut() {
    slot.hidden = false;
    slot.innerHTML = '<button type="button" class="theme-toggle" data-sign-in-button>' + escapeHtml(attr("data-sign-in")) + "</button>";
    slot.querySelector("[data-sign-in-button]").addEventListener("click", function () {
      if (!window.Clerk) return;
      if (typeof Clerk.openSignIn === "function") {
        Clerk.openSignIn({});
        return;
      }
      var dialog = document.getElementById("sign-in-dialog");
      if (!dialog) {
        dialog = document.createElement("dialog");
        dialog.id = "sign-in-dialog";
        dialog.setAttribute("data-no-edit", "");
        var mount = document.createElement("div");
        var close = document.createElement("button");
        close.type = "button";
        close.className = "theme-toggle";
        close.textContent = attr("data-done");
        close.addEventListener("click", function () {
          if (typeof Clerk.unmountSignIn === "function") Clerk.unmountSignIn(mount);
          dialog.close();
        });
        dialog.appendChild(mount);
        dialog.appendChild(close);
        document.body.appendChild(dialog);
        Clerk.mountSignIn(mount);
      }
      if (dialog.showModal && !dialog.open) dialog.showModal();
    });
  }

  function renderSignedIn() {
    slot.hidden = false;
    slot.innerHTML =
      '<div id="user-button"></div>' +
      '<button type="button" class="theme-toggle" data-edit-toggle aria-pressed="false" disabled title="' + escapeHtml(attr("data-hint")) + '">' + escapeHtml(attr("data-label-edit")) + "</button>" +
      '<button type="button" class="theme-toggle" data-reset-page disabled>' + escapeHtml(attr("data-reset")) + "</button>" +
      '<span class="edit-status" data-edit-status aria-live="polite"></span>';
    var userButton = document.getElementById("user-button");
    if (window.Clerk && userButton) Clerk.mountUserButton(userButton);
    var toggle = slot.querySelector("[data-edit-toggle]");
    var reset = slot.querySelector("[data-reset-page]");
    toggle.addEventListener("click", function () {
      if (!ready) return;
      if (editing) {
        var active = document.activeElement;
        if (active && active.getAttribute && active.getAttribute("data-edit")) saveUnit(active);
      }
      editing = !editing;
      toggle.setAttribute("aria-pressed", editing ? "true" : "false");
      toggle.textContent = editing ? attr("data-done") : attr("data-label-edit");
      markEditable(editing);
    });
    reset.addEventListener("click", function () {
      if (!ready) return;
      if (!window.confirm(attr("data-confirm"))) return;
      api("DELETE", { path: pagePath(), reset: true }).then(function () {
        edits = Object.create(null);
        units().forEach(function (el) {
          if (el.hasAttribute("data-original")) el.textContent = el.getAttribute("data-original");
        });
        setStatus(attr("data-saved"));
      }).catch(function () {
        setStatus(attr("data-error"));
      });
    });
    ready = false;
    loadEdits().then(function () {
      toggle.disabled = false;
      reset.disabled = false;
    }).catch(function () {
      setStatus(attr("data-error"));
    });
  }

  function syncSession() {
    var now = !!(window.Clerk && Clerk.isSignedIn);
    if (now === signedIn && slot.querySelector(now ? "[data-edit-toggle]" : "[data-sign-in-button]")) return;
    if (signedIn && !now) clearPersonalText();
    signedIn = now;
    if (now) renderSignedIn();
    else renderSignedOut();
  }

  function loadScript(src, attributes) {
    return new Promise(function (resolve, reject) {
      var script = document.createElement("script");
      script.src = src;
      script.async = true;
      script.crossOrigin = "anonymous";
      if (attributes) {
        Object.keys(attributes).forEach(function (name) {
          script.setAttribute(name, attributes[name]);
        });
      }
      script.onload = function () { resolve(); };
      script.onerror = function () { reject(new Error("script")); };
      document.head.appendChild(script);
    });
  }

  function clerkDomain(publishableKey) {
    var payload = String(publishableKey).split("_")[2] || "";
    var pad = payload.length % 4 === 0 ? "" : new Array(5 - (payload.length % 4)).join("=");
    return atob(payload + pad).replace(/\$/g, "");
  }

  function startClerk(publishableKey) {
    var domain;
    try {
      domain = clerkDomain(publishableKey);
    } catch (error) {
      return;
    }
    if (!domain || domain.indexOf("/") !== -1) return;
    var ui = "https://" + domain + "/npm/@clerk/ui@1/dist/ui.browser.js";
    var core = "https://" + domain + "/npm/@clerk/clerk-js@6/dist/clerk.browser.js";
    return loadScript(ui).then(function () {
      return loadScript(core, { "data-clerk-publishable-key": publishableKey });
    }).then(function () {
      if (!window.Clerk || typeof Clerk.load !== "function") return;
      return Clerk.load({ ui: { ClerkUI: window.__internal_ClerkUICtor } });
    }).then(function () {
      if (!window.Clerk) return;
      Clerk.addListener(function () { syncSession(); });
      syncSession();
    });
  }

  fetch("/api/auth-config", { headers: { Accept: "application/json" } })
    .then(function (res) { return res.ok ? res.json() : null; })
    .then(function (config) {
      if (!config || !config.enabled || !config.publishableKey) return;
      return startClerk(config.publishableKey);
    })
    .catch(function () {});
})();
