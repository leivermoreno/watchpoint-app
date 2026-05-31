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

document.addEventListener("DOMContentLoaded", renderLocalDates);
