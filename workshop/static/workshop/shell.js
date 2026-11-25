(() => {
  const toggle = document.querySelector('.menu-toggle');
  const navigation = document.getElementById('main-navigation');
  if (!toggle || !navigation) return;

  const narrow = window.matchMedia('(max-width:850px)');
  document.body.classList.add('nav-enhanced');

  function setOpen(open) {
    document.body.classList.toggle('navigation-open', open);
    toggle.setAttribute('aria-expanded', String(open || !narrow.matches));
  }

  function resetMenu() {
    if (narrow.matches && navigation.contains(document.activeElement)) toggle.focus();
    setOpen(false);
  }

  resetMenu();
  narrow.addEventListener('change', resetMenu);
  toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.classList.contains('navigation-open')) {
      setOpen(false);
      toggle.focus();
    }
  });
})();
