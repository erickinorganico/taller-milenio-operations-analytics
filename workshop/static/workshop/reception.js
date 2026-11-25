(() => {
  const field = document.querySelector('[data-vehicle-filter]');
  if (!field) return;
  const search = field.querySelector('input');
  const select = document.getElementById(search.getAttribute('aria-controls'));
  const review = document.querySelector('[data-review-vehicle]');
  function syncReview() {
    if (!review) return;
    const sameVehicle = select.value === review.dataset.reviewVehicle;
    const confirm = select.form.elements.confirm_open_orders;
    confirm.required = sameVehicle;
    if (!sameVehicle) confirm.checked = false;
    confirm.disabled = !sameVehicle;
    confirm.closest('label').hidden = !sameVehicle;
    review.hidden = !sameVehicle;
    select.form.querySelector('[data-create-order]').textContent = sameVehicle
      ? 'Crear otra orden' : 'Crear orden de trabajo';
  }
  syncReview();
  select.addEventListener('change', syncReview);
  const [placeholder, ...vehicles] = select.options;
  if (vehicles.length < 2) return;
  const status = field.querySelector('[data-vehicle-count]');
  const normalize = text => text.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().replace(/[\s-]+/g, '');
  const entries = vehicles.map(option => [option, normalize(option.textContent)]);
  field.hidden = false;

  search.addEventListener('input', () => {
    const previous = select.value;
    const query = normalize(search.value);
    const matches = entries.filter(([, label]) => label.includes(query)).map(([option]) => option);
    select.replaceChildren(placeholder, ...matches);
    select.value = matches.some(option => option.value === previous) ? previous : '';
    syncReview();
    status.textContent = matches.length
      ? (matches.length === 1 ? 'Un vehículo encontrado. Selecciónalo en la lista.' : `${matches.length} vehículos encontrados. Elige uno en la lista.`)
      : 'Sin coincidencias. Revisa la placa o registra el vehículo.';
  });
  search.addEventListener('keydown', event => {
    if (event.key === 'Enter') {
      event.preventDefault();
      select.focus();
    }
  });
})();
