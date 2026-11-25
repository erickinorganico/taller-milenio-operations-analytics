const pendingButtons = new Map();
document.querySelectorAll('form').forEach(form => {
  form.addEventListener('submit', event => {
    if (event.defaultPrevented) return;
    if (form.dataset.confirm && !window.confirm(form.dataset.confirm)) {
      event.preventDefault();
      return;
    }
    const button = event.submitter;
    if (!button) return;
    pendingButtons.set(button, {disabled: button.disabled, label: button.textContent});
    setTimeout(() => {
      if (!pendingButtons.has(button)) return;
      button.disabled = true;
      button.textContent = form.method.toLowerCase() === 'get' ? 'Aplicando…' : 'Guardando…';
    }, 0);
  });
});
// Back/forward can restore a document while keeping its disabled submit button.
window.addEventListener('pageshow', () => {
  pendingButtons.forEach((original, button) => {
    button.disabled = original.disabled;
    button.textContent = original.label;
  });
  pendingButtons.clear();
});
// Keep the selected list view when paging or submitting empty filter fields.
function listView(url) {
  const selected = new URLSearchParams();
  for (const [key, value] of url.searchParams) {
    if (key !== 'page' && value) selected.append(key, value);
  }
  selected.sort();
  return url.pathname + '?' + selected.toString();
}
const currentView = listView(new URL(window.location.href));
document.querySelectorAll('nav a').forEach(link => {
  if (link.closest('[data-list-views]')) {
    if (listView(new URL(link.href)) === currentView) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  } else if (link.getAttribute('href') === location.pathname) {
    link.setAttribute('aria-current', 'page');
  }
});

document.querySelectorAll("[data-print]").forEach(button=>button.addEventListener("click",()=>window.print()));
