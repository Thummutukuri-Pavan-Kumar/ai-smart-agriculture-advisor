// frontend/scripts/i18n.js
// Clean, error-free, production-ready version

/*(function () {
  const TRANSLATION_PATH = "../translations/";       // pages/... -> ../translations/lang.json
  const DEFAULT_LANG = "en";
  const LS_KEY = "selected_lang";

  let currentLang = localStorage.getItem(LS_KEY) || DEFAULT_LANG;
  let translations = {};

  function log(...args) {
    if (window.__DEBUG_I18N) console.log("[i18n]", ...args);
  }

  // ---------------------------
  // Load translation file
  // ---------------------------
  async function loadTranslations(lang) {
    const url = `${TRANSLATION_PATH}${lang}.json`;

    try {
      const res = await fetch(url, { cache: "no-cache" });
      if (!res.ok) throw new Error(`Failed to load ${url}`);

      translations = await res.json();
      currentLang = lang;

      localStorage.setItem(LS_KEY, lang);
      document.documentElement.lang = lang;

      applyTranslations();
      return true;
    } catch (err) {
      console.error("[i18n] load error:", err);

      if (lang !== DEFAULT_LANG) {
        console.warn(`[i18n] Falling back to ${DEFAULT_LANG}`);
        return loadTranslations(DEFAULT_LANG);
      }
      return false;
    }
  }

  // ---------------------------
  // Key Resolver
  // ---------------------------
  function getKey(key) {
    if (!key) return "";

    const parts = key.split(".");
    let node = translations;

    for (let p of parts) {
      if (node && typeof node === "object" && p in node) {
        node = node[p];
      } else {
        return undefined;
      }
    }
    return node;
  }

  // ---------------------------
  // Replace {variables}
  // ---------------------------
  function interpolate(str = "", vars = {}) {
    return str.replace(/\{([\w\d_]+)\}/g, (_, k) => (k in vars ? vars[k] : _));
  }

  // ---------------------------
  // Public translate helper
  // ---------------------------
  function t(key, vars = {}) {
    const val = getKey(key);
    if (val === undefined) return `[${key}]`;

    if (typeof val === "string") return interpolate(val, vars);
    return JSON.stringify(val);
  }

  // ---------------------------
  // Apply translations to DOM
  // ---------------------------
  function applyTranslations(root = document) {
    // Text replacements
    root.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      const varsAttr = el.getAttribute("data-i18n-vars");

      let vars = {};
      if (varsAttr) {
        try {
          vars = JSON.parse(varsAttr);
        } catch {}
      }

      const translated = t(key, vars);

      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
        if (!el.value) el.value = translated;
      } else {
        el.textContent = translated;
      }
    });

    // Attribute translations
    root.querySelectorAll("[data-i18n-attr]").forEach((el) => {
      const raw = el.getAttribute("data-i18n-attr");
      raw.split(";")
        .map((s) => s.trim())
        .filter(Boolean)
        .forEach((pair) => {
          const [attr, key] = pair.split(":").map((x) => x.trim());
          if (!attr || !key) return;
          el.setAttribute(attr, t(key));
        });
    });

    // HTML translations
    root.querySelectorAll("[data-i18n-html]").forEach((el) => {
      const key = el.getAttribute("data-i18n-html");
      const val = getKey(key);
      if (val !== undefined) el.innerHTML = val;
    });
  }

  // ---------------------------
  // Public setter
  // ---------------------------
  async function setLanguage(lang) {
    if (!lang) return;
    if (lang === currentLang) return true;
    return loadTranslations(lang);
  }

  // ---------------------------
  // Bootstrap
  // ---------------------------
  document.addEventListener("DOMContentLoaded", async () => {
    await loadTranslations(currentLang);

    // expose globally
    window.i18n = { setLanguage, t, currentLang: () => currentLang, applyTranslations };
  });

  // Sync across browser tabs
  window.addEventListener("storage", (e) => {
    if (e.key === LS_KEY && e.newValue && e.newValue !== currentLang) {
      loadTranslations(e.newValue);
    }
  });

  // expose immediately
  window.i18n = { setLanguage, t, currentLang: () => currentLang, applyTranslations };
})(); */
// frontend/scripts/i18n.js
// Robust i18n loader — uses root-based path so it works from / or /pages/...
/*(function () {
  // Root-based path ensures consistent resolution when served from different folders
  const TRANSLATION_PATH = "/translations/"; // -> /translations/<lang>.json
  const DEFAULT_LANG = "en";
  const LS_KEY = "selected_lang";

  let currentLang = localStorage.getItem(LS_KEY) || DEFAULT_LANG;
  let translations = {};

  function log(...args) {
    if (window.__DEBUG_I18N) console.log("[i18n]", ...args);
  }

  async function fetchJsonNoCache(url) {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status} loading ${url}`);
    return res.json();
  }

  // Load translation file
  async function loadTranslations(lang) {
    const url = `${TRANSLATION_PATH}${lang}.json`;
    try {
      translations = await fetchJsonNoCache(url);
      currentLang = lang;
      localStorage.setItem(LS_KEY, lang);
      document.documentElement.lang = lang;
      applyTranslations();
      log("loaded", lang);
      return true;
    } catch (err) {
      console.error("[i18n] load error:", err);
      if (lang !== DEFAULT_LANG) {
        console.warn(`[i18n] Falling back to ${DEFAULT_LANG}`);
        // try fallback once
        return loadTranslations(DEFAULT_LANG);
      }
      return false;
    }
  }

  // Key resolver
  function getKey(key) {
    if (!key) return "";
    const parts = key.split(".");
    let node = translations;
    for (let p of parts) {
      if (node && typeof node === "object" && p in node) {
        node = node[p];
      } else {
        return undefined;
      }
    }
    return node;
  }

  // Replace {vars}
  function interpolate(str = "", vars = {}) {
    return str.replace(/\{([\w\d_]+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
  }

  // Public translate helper
  function t(key, vars = {}) {
    const val = getKey(key);
    if (val === undefined) return `[${key}]`;
    if (typeof val === "string") return interpolate(val, vars);
    return JSON.stringify(val);
  }

  // Apply translations to DOM (scoped to root)
  function applyTranslations(root = document) {
    // text replacements
    root.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      const varsAttr = el.getAttribute("data-i18n-vars");
      let vars = {};
      if (varsAttr) {
        try {
          vars = JSON.parse(varsAttr);
        } catch (e) {
          // ignore bad JSON
        }
      }
      const translated = t(key, vars);
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
        if (!el.value) el.value = translated;
      } else {
        el.textContent = translated;
      }
    });

    // attribute translations: data-i18n-attr="title:page.title; placeholder:form.name"
    root.querySelectorAll("[data-i18n-attr]").forEach((el) => {
      const raw = el.getAttribute("data-i18n-attr") || "";
      raw.split(";")
        .map((s) => s.trim())
        .filter(Boolean)
        .forEach((pair) => {
          const [attr, key] = pair.split(":").map((x) => x && x.trim());
          if (!attr || !key) return;
          el.setAttribute(attr, t(key));
        });
    });

    // html content translations
    root.querySelectorAll("[data-i18n-html]").forEach((el) => {
      const key = el.getAttribute("data-i18n-html");
      const val = getKey(key);
      if (val !== undefined) el.innerHTML = val;
    });
  }

  // Set language (public)
  async function setLanguage(lang) {
    if (!lang) return;
    if (lang === currentLang) return true;
    return loadTranslations(lang);
  }

  // Bootstrap on DOMContentLoaded
  document.addEventListener("DOMContentLoaded", async () => {
    await loadTranslations(currentLang);
    // expose API
    window.i18n = { setLanguage, t, currentLang: () => currentLang, applyTranslations };
  });

  // sync across tabs
  window.addEventListener("storage", (e) => {
    if (e.key === LS_KEY && e.newValue && e.newValue !== currentLang) {
      loadTranslations(e.newValue);
    }
  });

  // expose immediately (safe to call before DOM content loaded)
  window.i18n = { setLanguage, t, currentLang: () => currentLang, applyTranslations };
})();*/
// frontend/scripts/i18n.js
// Robust, production-ready i18n helper for your static frontend.
// Requirements: serve /translations/<lang>.json from web server (root-based path).
(function () {
  "use strict";

  // CONFIG
  const TRANSLATION_PATH = "/translations/"; // must be served from site root: /translations/en.json, /translations/hi.json ...
  const DEFAULT_LANG = "en";
  const LS_KEY = "selected_lang";

  // state
  let currentLang = localStorage.getItem(LS_KEY) || DEFAULT_LANG;
  let translations = {};

  // small helpers
  function debug(...args) {
    if (window.__DEBUG_I18N) console.log("[i18n]", ...args);
  }
  function safeJsonParse(s) { try { return JSON.parse(s); } catch { return null; } }

  // fetch JSON with no-cache
  async function fetchJsonNoCache(url) {
    const res = await fetch(url, { cache: "no-cache" });
    if (!res.ok) throw new Error(`HTTP ${res.status} loading ${url}`);
    return res.json();
  }

  // load translations for a language (returns true on success)
  async function loadTranslations(lang) {
    if (!lang) return false;
    const url = `${TRANSLATION_PATH}${lang}.json`;
    debug("loading", url);

    try {
      const data = await fetchJsonNoCache(url);
      translations = typeof data === "object" && data !== null ? data : {};
      currentLang = lang;
      localStorage.setItem(LS_KEY, lang);
      document.documentElement.lang = lang;

      // apply to document and update title if translation provided
      applyTranslations(document);
      _applyTitleTranslation();
      debug("loaded", lang, Object.keys(translations).length, "keys");
      return true;
    } catch (err) {
      console.error("[i18n] load error:", err);
      if (lang !== DEFAULT_LANG) {
        debug("falling back to default:", DEFAULT_LANG);
        return loadTranslations(DEFAULT_LANG);
      }
      return false;
    }
  }

  // Resolve nested key "dashboard.daily_wisdom" -> translations.dashboard.daily_wisdom
  function getKey(key) {
    if (!key) return "";
    const parts = key.split(".");
    let node = translations;
    for (const p of parts) {
      if (node && typeof node === "object" && p in node) {
        node = node[p];
      } else {
        return undefined;
      }
    }
    return node;
  }

  // Interpolate {var}
  function interpolate(str = "", vars = {}) {
    return String(str).replace(/\{([\w\d_]+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
  }

  // Public translate helper
  function t(key, vars = {}) {
    const val = getKey(key);
    if (val === undefined) return `[${key}]`;
    if (typeof val === "string") return interpolate(val, vars);
    // if val is object/array return JSON string (caller may want to parse)
    return JSON.stringify(val);
  }

  // Apply translations to DOM subtree (default document)
  // Supports:
  //  - data-i18n="path.to.key" -> textContent OR input.value (only if empty)
  //  - data-i18n-attr="placeholder:form.name; title:page.title"
  //  - data-i18n-html="key" -> innerHTML
  function applyTranslations(root = document) {
    if (!root || !(root.querySelectorAll)) return;

    // TEXT replacements
    root.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.getAttribute("data-i18n");
      const varsAttr = el.getAttribute("data-i18n-vars");
      let vars = {};
      if (varsAttr) {
        const parsed = safeJsonParse(varsAttr);
        if (parsed) vars = parsed;
      }

      const translated = t(key, vars);
      // If element is <title> or meta we handle separately; but generic rule:
      if (el.tagName === "INPUT" || el.tagName === "TEXTAREA") {
        // set placeholder or value depending on attribute presence
        const setAs = el.getAttribute("data-i18n-set") || "placeholder"; // default placeholder for inputs
        if (setAs === "value") {
          el.value = translated;
        } else {
          // placeholder
          if (el.placeholder === "" || el.getAttribute("data-i18n-force") === "true") {
            el.placeholder = translated;
          }
        }
      } else {
        el.textContent = translated;
      }
    });

    // ATTRIBUTE replacements: data-i18n-attr="title:page.title; placeholder:form.name"
    root.querySelectorAll("[data-i18n-attr]").forEach((el) => {
      const raw = el.getAttribute("data-i18n-attr") || "";
      raw.split(";").map(s => s.trim()).filter(Boolean).forEach(pair => {
        const parts = pair.split(":");
        if (parts.length < 2) return;
        const attr = parts[0].trim();
        const key = parts.slice(1).join(":").trim();
        if (!attr || !key) return;
        const translated = t(key);
        if (attr === "innerHTML") {
          el.innerHTML = translated;
        } else if (attr === "textContent") {
          el.textContent = translated;
        } else {
          el.setAttribute(attr, translated);
        }
      });
    });

    // HTML replacements
    root.querySelectorAll("[data-i18n-html]").forEach((el) => {
      const key = el.getAttribute("data-i18n-html");
      const val = getKey(key);
      if (val !== undefined) el.innerHTML = (typeof val === "string") ? val : JSON.stringify(val);
    });

    // Update document title if present on any element or leave existing title
    _applyTitleTranslation();
  }

  // internal: if translations contains "page.title" or "document.title" update document.title
  function _applyTitleTranslation() {
    const titleKeyCandidates = ["page.title", "document.title", "dashboard.title", "title"];
    for (const k of titleKeyCandidates) {
      const v = getKey(k);
      if (typeof v === "string" && v.trim()) {
        document.title = v;
        break;
      }
    }
  }

  // Public setter to change language
  async function setLanguage(lang) {
    if (!lang) return false;
    if (lang === currentLang) {
      debug("setLanguage: same as current", lang);
      return true;
    }
    const ok = await loadTranslations(lang);
    if (ok) {
      // notify others
      try { localStorage.setItem(LS_KEY, lang); } catch (e) {}
    }
    // update visible language label if any
    const langLabelEl = document.getElementById("langLabel");
    if (langLabelEl) langLabelEl.textContent = (lang || "en").toUpperCase();
    return ok;
  }

  // Sync across tabs: when LS_KEY changes, reload translations
  window.addEventListener("storage", (e) => {
    if (e.key === LS_KEY && e.newValue && e.newValue !== currentLang) {
      debug("storage event, switching lang to", e.newValue);
      loadTranslations(e.newValue).catch(err => debug("loadTranslations error", err));
    }
  });

  // Bootstrap on DOMContentLoaded
  document.addEventListener("DOMContentLoaded", async () => {
    try {
      await loadTranslations(currentLang);
    } catch (e) {
      console.warn("i18n bootstrap failed", e);
    }
    // expose API
    window.i18n = {
      setLanguage,
      t,
      currentLang: () => currentLang,
      applyTranslations
    };
    debug("i18n ready currentLang=", currentLang);
  });

  // Expose immediately in case code calls it before DOMContentLoaded
  window.i18n = window.i18n || {
    setLanguage,
    t,
    currentLang: () => currentLang,
    applyTranslations
  };

})();

