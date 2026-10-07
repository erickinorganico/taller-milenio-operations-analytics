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
document.querySelectorAll('nav a').forEach(link=>{if(link.getAttribute('href')===location.pathname)link.setAttribute('aria-current','page');});

document.querySelectorAll("[data-print]").forEach(button=>button.addEventListener("click",()=>window.print()));
