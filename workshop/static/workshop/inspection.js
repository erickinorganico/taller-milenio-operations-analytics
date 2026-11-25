(() => {
  const panel = document.querySelector('#inspection[data-feed]');
  if (!panel || !window.fetch || !window.FormData) return;

  const list = panel.querySelector('[data-inspections]');
  const sync = panel.querySelector('[data-sync]');
  const form = panel.querySelector('[data-inspection-form]');
  let revision = panel.dataset.revision;
  let refreshing = false;

  async function refresh(manual = false) {
    if (refreshing || document.hidden) return;
    refreshing = true;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 18000);
    try {
      const url = new URL(panel.dataset.feed, location.href);
      url.searchParams.set('revision', revision);
      const response = await fetch(url, {cache: 'no-store', signal: controller.signal});
      if (response.redirected || [401, 403, 404].includes(response.status)) {
        list.textContent = '';
        revision = '';
        sync.textContent = 'Abre de nuevo la orden con una cuenta que tenga acceso.';
        return;
      }
      if (response.status === 204) {
        if (manual || sync.textContent) sync.textContent = 'La lista está al día.';
        return;
      }
      if (!response.ok) throw new Error();
      const result = await response.json();
      list.innerHTML = result.html;
      revision = result.revision;
      if (form) {
        const canAdd = result.stage === 'inspection';
        panel.querySelector('[data-stage-help]').hidden = canAdd;
        // Preserve a draft if another device moves the order to a new stage.
        panel.querySelector('[data-entry]').hidden = !canAdd && !form.dataset.edited;
      }
      sync.textContent = 'Lista de inspecciones actualizada.';
    } catch {
      sync.textContent = 'Sin sincronizar. Comprueba la conexión y toca Actualizar.';
    } finally {
      clearTimeout(timer);
      refreshing = false;
    }
  }

  panel.querySelector('[data-refresh]').addEventListener('click', event => {
    event.preventDefault();
    refresh(true);
  });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) refresh(); });
  window.addEventListener('online', () => refresh());
  window.setInterval(() => refresh(), 20000);
  if (!form) return;

  const camera = form.elements.photo;
  const gallery = form.elements.gallery_photo;
  const preview = form.querySelector('[data-preview]');
  const removePhoto = form.querySelector('[data-remove-photo]');
  const feedback = form.querySelector('[data-upload-status]');
  const button = form.querySelector('button[type=submit]');
  const key = form.elements.submission_key;
  let selection = 0;
  let prepared = null;
  let uploading = false;
  function warnBeforeLeaving(event) {
    event.preventDefault();
    event.returnValue = '';
  }
  function updateDraft() {
    const hasDraft = camera.files.length || gallery.files.length ||
      form.elements.area.value.trim() || form.elements.notes.value.trim() || form.elements.result.value;
    if (hasDraft) {
      form.dataset.edited = 'true';
      window.addEventListener('beforeunload', warnBeforeLeaving);
    } else {
      delete form.dataset.edited;
      window.removeEventListener('beforeunload', warnBeforeLeaving);
    }
  }
  form.addEventListener('input', updateDraft);
  updateDraft();

  async function prepare(file, version) {
    if (file.size > 25 * 1024 * 1024) throw new Error('La foto supera 25 MB. Elige una copia más pequeña.');
    const data = await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('No se pudo abrir la foto. Selecciónala de nuevo.'));
      reader.readAsDataURL(file);
    });
    const picture = new Image();
    picture.src = data;
    try {
      await picture.decode();
    } catch {
      throw new Error('El navegador no pudo abrir la foto. Elige JPG, PNG o WebP. En iPhone puedes usar el formato Más compatible.');
    }
    if (version !== selection) return null;
    if (file.size <= 5 * 1024 * 1024 && Math.max(picture.width, picture.height) <= 2400
        && ['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      preview.src = data;
      preview.hidden = false;
      return file;
    }
    const scale = Math.min(1, 2400 / Math.max(picture.width, picture.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.max(1, Math.round(picture.width * scale));
    canvas.height = Math.max(1, Math.round(picture.height * scale));
    const context = canvas.getContext('2d');
    context.fillStyle = '#ffffff';
    context.fillRect(0, 0, canvas.width, canvas.height);
    context.drawImage(picture, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.88));
    if (!blob || blob.size > 5 * 1024 * 1024) throw new Error('No se pudo reducir la foto. Elige una copia más pequeña.');
    if (version !== selection) return null;
    preview.src = canvas.toDataURL('image/jpeg', 0.55);
    preview.hidden = false;
    return blob;
  }

  for (const [input, other] of [[camera, gallery], [gallery, camera]]) {
    input.addEventListener('change', () => {
      if (input.files.length) other.value = '';
      const version = ++selection;
      const file = camera.files[0] || gallery.files[0];
      removePhoto.hidden = !file;
      updateDraft();
      preview.hidden = true;
      preview.removeAttribute('src');
      feedback.textContent = file ? 'Preparando la foto…' : '';
      prepared = file ? prepare(file, version).then(blob => {
        if (version === selection) feedback.textContent = 'Foto lista. Toca Guardar inspección.';
        return {blob};
      }).catch(error => {
        if (version === selection) feedback.textContent = error.message;
        return {error};
      }) : null;
    });
  }

  removePhoto.addEventListener('click', () => {
    camera.value = '';
    gallery.value = '';
    camera.dispatchEvent(new Event('change'));
    feedback.textContent = 'Foto retirada. Puedes elegir otra o guardar sólo el punto.';
    camera.focus();
  });

  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (uploading) return;
    uploading = true;
    button.disabled = true;
    removePhoto.disabled = true;
    const payload = new FormData(form);
    const inputs = [...form.querySelectorAll('input:not([type=hidden]), select, textarea')];
    inputs.forEach(input => { input.disabled = true; });
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 90000);
    try {
      if (prepared) {
        const {blob, error} = await prepared;
        if (error) { feedback.textContent = error.message; return; }
        payload.delete('gallery_photo');
        payload.set('photo', blob, 'inspeccion.jpg');
      }
      // Login in a second tab rotates the CSRF secret. Verify the same person
      // still owns this form before transmitting any vehicle photo.
      const sessionUrl = new URL(panel.dataset.feed, location.href);
      sessionUrl.searchParams.set('session', '1');
      const session = await fetch(sessionUrl, {cache: 'no-store', signal: controller.signal});
      if (session.redirected || [401, 403, 404].includes(session.status)) {
        feedback.textContent = 'Abre tu sesión en otra pestaña y vuelve aquí con la cuenta que inició el punto.';
        return;
      }
      if (!session.ok) throw new Error();
      const access = await session.json();
      if (access.actor !== form.elements.submission_actor.value) {
        feedback.textContent = 'Cambió la cuenta del taller. Vuelve a iniciar sesión con la cuenta que abrió esta orden.';
        return;
      }
      payload.set('csrfmiddlewaretoken', access.csrf);
      feedback.textContent = 'Enviando al taller…';
      const response = await fetch(form.action, {
        method: 'POST', headers: {Accept: 'application/json'}, body: payload, signal: controller.signal
      });
      if (response.redirected || [401, 403].includes(response.status)) {
        feedback.textContent = 'Revisa tu sesión en otra pestaña y vuelve a intentar desde aquí.';
        return;
      }
      if (response.status === 413) {
        feedback.textContent = 'La foto supera el límite de envío. Elige una copia más pequeña.';
        return;
      }
      const result = await response.json();
      if (!response.ok) {
        feedback.textContent = result.error || 'No se confirmó el envío. Reintenta desde aquí.';
        return;
      }
      form.reset();
      key.value = result.next_key;
      updateDraft();
      prepared = null;
      selection++;
      preview.hidden = true;
      preview.removeAttribute('src');
      removePhoto.hidden = true;
      feedback.textContent = result.message;
      refresh(true);
    } catch {
      feedback.textContent = 'Sin confirmación. Conserva esta página, recupera la conexión y toca Guardar inspección otra vez.';
    } finally {
      clearTimeout(timer);
      button.disabled = false;
      removePhoto.disabled = false;
      inputs.forEach(input => { input.disabled = false; });
      uploading = false;
    }
  }, true);
})();
