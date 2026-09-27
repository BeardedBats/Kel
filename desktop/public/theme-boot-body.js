// Set Arco's theme on <body> before the first paint (CP-13: no inline scripts).
(function () {
  try {
    var theme = localStorage.getItem('__aionui_theme');
    if (theme) document.body.setAttribute('arco-theme', theme);
  } catch (e) {}
})();
