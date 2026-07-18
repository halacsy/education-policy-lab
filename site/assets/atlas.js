(function () {
  var root = document.documentElement;
  var nav = document.querySelector('[data-site-nav]');
  var toggle = document.querySelector('[data-nav-toggle]');

  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', String(open));
    });
  }

  document.querySelectorAll('[data-set-lang]').forEach(function (button) {
    button.addEventListener('click', function () {
      var lang = button.getAttribute('data-set-lang');
      root.lang = lang;
      document.querySelectorAll('[data-set-lang]').forEach(function (candidate) {
        candidate.setAttribute('aria-pressed', String(candidate === button));
      });
      try { window.localStorage.setItem('atlas-language', lang); } catch (_) {}
    });
  });

  try {
    var saved = window.localStorage.getItem('atlas-language');
    var savedButton = saved && document.querySelector('[data-set-lang="' + saved + '"]');
    if (savedButton) savedButton.click();
  } catch (_) {}
})();
