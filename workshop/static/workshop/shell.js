(() => {
  const toggle = document.querySelector('.menu-toggle');
  const navigation = document.getElementById('main-navigation');
  if (!toggle || !navigation) return;
  document.body.classList.add('nav-enhanced');
  const setOpen = open => {
    document.body.classList.toggle('navigation-open', open);
    toggle.setAttribute('aria-expanded', String(open));
    toggle.setAttribute('aria-label', open ? 'Ocultar navegación' : 'Mostrar navegación');
  };
  setOpen(false);
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    setOpen(open);
    if (open) navigation.querySelector('a').focus();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && document.body.classList.contains('navigation-open')) {
      setOpen(false);
      toggle.focus();
    }
  });
})();
