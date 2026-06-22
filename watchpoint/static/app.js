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
      if (panel && activeElement !== input && !panel.contains(activeElement)) {
        toggleAutocompletePanel(input, false);
      }
    }, 100);
  });

  document.addEventListener("pointerdown", (event) => {
    autocompleteInputs().forEach((input) => {
      const panel = autocompletePanelFor(input);
      if (panel && event.target !== input && !panel.contains(event.target)) {
        toggleAutocompletePanel(input, false);
      }
    });
  });

  document.body.addEventListener("htmx:afterSwap", (event) => {
    autocompleteInputs().forEach((input) => {
      const panel = autocompletePanelFor(input);
      if (!panel || event.target !== panel) {
        return;
      }

      toggleAutocompletePanel(input, document.activeElement === input);
    });
  });
}

document.addEventListener("DOMContentLoaded", renderLocalDates);
document.addEventListener("DOMContentLoaded", bindAutocompleteDismissal);
