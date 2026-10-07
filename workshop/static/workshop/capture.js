const reading = document.querySelector('[data-capture-status]');
if (reading) {
  let attempts = 0;
  const poll = () => {
    if (++attempts > 75) {
      reading.textContent = 'La lectura sigue pendiente. Puedes volver a la bandeja y abrir el documento más tarde.';
      return;
    }
    fetch(reading.dataset.captureStatus, {cache:'no-store'})
      .then(response => response.ok ? response.json() : Promise.reject())
      .then(result => {
        if (!['pending', 'reading'].includes(result.status)) location.reload();
        else setTimeout(poll, 2000);
      })
      .catch(() => { reading.textContent = 'No pudimos consultar el estado. Actualiza la página para continuar.'; });
  };
  setTimeout(poll, 2000);
}
