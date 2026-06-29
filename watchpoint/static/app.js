// Render server-emitted UTC timestamps in the viewer's local timezone.
// Backend stores/sends instants in UTC; the browser is the authority on the
// viewer's timezone. Targets <time class="local-date" datetime="<ISO-8601 UTC>">
// elements and rewrites their text in the viewer's locale/timezone.
function renderLocalDates() {
  document.querySelectorAll("time.local-date").forEach((el) => {
    const d = new Date(el.dateTime);
    if (!isNaN(d)) {
      el.textContent = d.toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      });
    }
  });
}

if (window.htmx) {
  window.htmx.config.historyRestoreAsHxRequest = false;
}

function autocompletePanelFor(input) {
  const panelId = input.getAttribute("aria-controls");
  if (!panelId) {
    return null;
  }

  const panel = document.getElementById(panelId);
  if (!panel || !panel.classList.contains("title-search-results")) {
    return null;
  }

  return panel;
}

function toggleAutocompletePanel(input, show) {
  const panel = autocompletePanelFor(input);
  if (panel) {
    panel.classList.toggle("d-none", !show || !panel.textContent.trim());
  }
}

function autocompleteInputHasText(input) {
  return input.value.trim().length > 0;
}

function titleSearchInput() {
  const input = document.getElementById("titleNameInput");
  return input instanceof HTMLInputElement ? input : null;
}

function cleanSearchQuery(value) {
  return value.split(/\s+/).filter(Boolean).join(" ");
}

function titleSearchQueryFromLocation() {
  const params = new URLSearchParams(window.location.search);
  return params.has("q") ? cleanSearchQuery(params.get("q") || "") : "";
}

function setTitleSearchPageState(input) {
  const page = input.closest(".search-page");
  if (page) {
    page.classList.toggle("search-page-has-query", autocompleteInputHasText(input));
  }
}

function restoreTitleSearchFromLocation() {
  const input = titleSearchInput();
  if (!input) {
    return;
  }

  const query = titleSearchQueryFromLocation();
  input.value = query;
  input.defaultValue = query;
  setTitleSearchPageState(input);
  toggleAutocompletePanel(input, autocompleteInputHasText(input));
}

function bindTitleSearchState() {
  const input = titleSearchInput();
  if (!input) {
    return;
  }

  setTitleSearchPageState(input);
  input.addEventListener("input", () => setTitleSearchPageState(input));
  input.addEventListener("search", () => setTitleSearchPageState(input));
}

function shouldKeepAutocompletePanelOpen(input) {
  return (
    input.dataset.keepResultsWhenPopulated === "true" &&
    autocompleteInputHasText(input)
  );
}

function shouldDismissAutocompletePanel(input) {
  return !shouldKeepAutocompletePanelOpen(input);
}

function autocompleteInputs() {
  return document.querySelectorAll("input[aria-controls]");
}

function bindAutocompleteDismissal() {
  document.addEventListener("focusin", (event) => {
    if (event.target instanceof HTMLInputElement) {
      toggleAutocompletePanel(event.target, true);
    }
  });

  document.addEventListener("focusout", (event) => {
    if (!(event.target instanceof HTMLInputElement)) {
      return;
    }

    const input = event.target;
    window.setTimeout(() => {
      const panel = autocompletePanelFor(input);
      const activeElement = document.activeElement;
      if (
        panel &&
        activeElement !== input &&
        !panel.contains(activeElement) &&
        shouldDismissAutocompletePanel(input)
      ) {
        toggleAutocompletePanel(input, false);
      }
    }, 100);
  });

  document.addEventListener("pointerdown", (event) => {
    autocompleteInputs().forEach((input) => {
      const panel = autocompletePanelFor(input);
      if (
        panel &&
        event.target !== input &&
        !panel.contains(event.target) &&
        shouldDismissAutocompletePanel(input)
      ) {
        toggleAutocompletePanel(input, false);
      }
    });
  });

  document.body.addEventListener("htmx:afterSwap", (event) => {
    autocompleteInputs().forEach((input) => {
      const panel = autocompletePanelFor(input);
      if (!panel || event.detail.target !== panel) {
        return;
      }

      toggleAutocompletePanel(
        input,
        document.activeElement === input || shouldKeepAutocompletePanelOpen(input),
      );
    });
  });
}

document.addEventListener("DOMContentLoaded", renderLocalDates);
document.addEventListener("DOMContentLoaded", bindTitleSearchState);
document.addEventListener("DOMContentLoaded", bindAutocompleteDismissal);
window.addEventListener("pageshow", restoreTitleSearchFromLocation);
