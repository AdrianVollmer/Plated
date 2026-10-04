// Tap-to-select for the ingredient/step quick-edit button on touch devices,
// where there's no hover to reveal it (see .quick-edit-btn in styles.css).

(function () {
  "use strict";

  const SELECTABLE = ".ingredient-item, .instruction-item";

  function clearSelection() {
    document.querySelectorAll(`${SELECTABLE}.selected`).forEach((item) => {
      item.classList.remove("selected");
    });
  }

  document.addEventListener("click", function (event) {
    const item = event.target.closest(SELECTABLE);

    if (!item) {
      clearSelection();
      return;
    }

    if (event.target.closest(".quick-edit-btn")) {
      return;
    }

    const wasSelected = item.classList.contains("selected");
    clearSelection();
    if (!wasSelected) {
      item.classList.add("selected");
    }
  });
})();
