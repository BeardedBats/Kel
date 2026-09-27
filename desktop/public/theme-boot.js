// Restore the saved theme before the first paint (no flash). A file rather than an inline script so
// the renderer's Content Security Policy can forbid inline scripts (CP-13).
(function () {
  try {
    var theme = localStorage.getItem('__aionui_theme');
    if (theme) document.documentElement.setAttribute('data-theme', theme);
  } catch (e) {}
})();
