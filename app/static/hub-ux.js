(function () {
  function showBusy(form) {
    if (!form) return;
    const btn = form.querySelector("button[type='submit']");
    if (btn && !btn.dataset.originalText) {
      btn.dataset.originalText = btn.innerText;
      btn.innerText = "Ukládám…";
      btn.disabled = true;
      btn.classList.add("is-loading");
    }
  }

  document.addEventListener("submit", function (e) {
    const form = e.target;
    if (!form || form.dataset.noBusy === "1") return;
    showBusy(form);
  }, true);

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("table").forEach(function (table) {
      if (!table.closest(".table-scroll")) return;
      table.classList.add("hub-fast-table");
    });

    document.querySelectorAll("input[placeholder*='Fulltext'], input[placeholder*='fulltext'], input[name='q']").forEach(function (input) {
      input.setAttribute("autocomplete", "off");
    });
  });
})();
