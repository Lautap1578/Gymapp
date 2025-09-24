// editar_rutinas.js — manejo de filas y guardado (FIX: dataset + opciones)
(function(){
  const tabla = document.getElementById('tabla-rutina');
  const tbody = tabla?.querySelector('tbody');
  const btnAgregar = document.getElementById('btn-agregar');
  const btnLimpiar = document.getElementById('btn-limpiar');
  const btnGuardar = document.getElementById('btn-guardar');
  const btnGuardarBottom = document.getElementById('btn-guardar-bottom');
  const semanaSelect = document.getElementById('semana-select');
  const formGuardar = document.getElementById('form-guardar');
  const payloadInput = document.getElementById('payload_input');
  const semanaIdInput = document.getElementById('semana_id_input');

  const nuevaFila = (data={}) => {
    const options = (window.__EJERCICIOS__ || []).map(e =>
      `<option value="${e.id}" ${e.id == (data.ejercicio_id ?? '') ? 'selected':''}>${e.text}</option>`
    ).join('');
    const tr = document.createElement('tr');
    // Construimos la fila con la nueva columna Rir y hacemos notas textarea para textos largos
    tr.innerHTML = `
      <td>
        <select name="ejercicio" class="input select" data-selected="${data.ejercicio_id ?? ''}" data-populated="1">
          ${options}
        </select>
      </td>
      <td><input type="number" min="1" name="series" class="input" value="${data.series ?? ''}" placeholder="3"></td>
      <td><input type="text" name="reps" class="input" value="${data.reps ?? ''}" placeholder="8-10"></td>
      <td><input type="number" min="0" name="kilos" class="input" value="${data.kilos ?? ''}" placeholder="0"></td>
      <td><input type="text" name="rir" class="input" value="${data.rir ?? ''}" placeholder="1-2"></td>
      <td><textarea name="notas" class="input notas-textarea" placeholder="Notas">${data.notas ?? ''}</textarea></td>
      <td class="acciones">
        <button class="icon-btn duplicate" title="Duplicar fila" aria-label="Duplicar">⎘</button>
        <button class="icon-btn remove" title="Eliminar fila" aria-label="Eliminar">✕</button>
      </td>
    `;
    return tr;
  };

  const onClickTable = (e) => {
    const btn = e.target.closest('.icon-btn');
    if(!btn) return;
    const tr = e.target.closest('tr');
    if(btn.classList.contains('remove')){
      tr?.remove();
      return;
    }
    if(btn.classList.contains('duplicate')){
      const clone = nuevaFila(leerFila(tr));
      tr.after(clone);
      if (window.__afterRowAdded) window.__afterRowAdded(clone);
      clone.querySelector('select,input')?.focus();
    }
  };

  const leerFila = (tr) => {
    const get = (sel) => tr.querySelector(sel);
    return {
      ejercicio_id: get('select[name="ejercicio"]')?.value || null,
      series: get('input[name="series"]')?.value || '',
      reps: get('input[name="reps"]')?.value || '',
      kilos: get('input[name="kilos"]')?.value || '',
      // Leer RIR y notas. Para notas priorizamos el textarea, si existe.
      rir: get('input[name="rir"]')?.value || '',
      notas: (tr.querySelector('textarea[name="notas"]')?.value || get('input[name="notas"]')?.value || ''),
    };
  };

  const serializar = () => {
    // Serializamos todas las filas incluyendo la columna Rir.  El JSON incluirá "rir" si corresponde
    const filas = [...tbody.querySelectorAll('tr')].map(leerFila);
    return JSON.stringify({ semana_id: semanaSelect?.value || null, filas });
  };

  const onGuardar = () => {
    if(!formGuardar) return;
    payloadInput.value = serializar();
    semanaIdInput.value = semanaSelect?.value || '';
    formGuardar.submit();
  };

  const onEnterNuevaFila = (e) => {
    if(e.key === 'Enter'){
      const tr = e.target.closest('tr');
      const isLast = tr && tr === tbody.lastElementChild;
      if(isLast){
        const nf = nuevaFila();
        tbody.appendChild(nf);
        if (window.__afterRowAdded) window.__afterRowAdded(nf);
        nf.querySelector('select,input')?.focus();
      }
    }
    if((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'd')){
      e.preventDefault();
      const tr = e.target.closest('tr');
      const clone = nuevaFila(leerFila(tr));
      tr.after(clone);
      if (window.__afterRowAdded) window.__afterRowAdded(clone);
      clone.querySelector('select,input')?.focus();
    }
    if(e.key === 'Delete'){
      const tr = e.target.closest('tr');
      const next = tr.nextElementSibling || tr.previousElementSibling;
      tr.remove();
      next?.querySelector('select,input')?.focus();
    }
  };

  btnAgregar?.addEventListener('click', () => {
    const nf = nuevaFila();
    tbody.appendChild(nf);
    if (window.__afterRowAdded) window.__afterRowAdded(nf);
    nf.querySelector('select,input')?.focus();
  });

  btnLimpiar?.addEventListener('click', () => {
    tbody.innerHTML = '';
    const nf = nuevaFila();
    tbody.appendChild(nf);
    if (window.__afterRowAdded) window.__afterRowAdded(nf);
  });

  // --- Rehidratar filas iniciales ---
  // Al cargar la página, si existen filas renderizadas desde el backend, las
  // convertimos a filas generadas con `nuevaFila` para unificar el comportamiento
  // y asegurar que Select2 se inicialice correctamente.  Esto soluciona el
  // problema de la primera fila sin resultados.
  document.addEventListener('DOMContentLoaded', () => {
    try {
      if (!tbody) return;
      const existentes = [...tbody.querySelectorAll('tr')];
      if (!existentes.length) return;
      const datos = existentes.map(leerFila);
      tbody.innerHTML = '';
      datos.forEach(d => {
        const nf = nuevaFila(d);
        tbody.appendChild(nf);
        if (window.__afterRowAdded) window.__afterRowAdded(nf);
      });
    } catch (e) {
      /* Silenciar errores para no bloquear otros scripts */
    }
  });

  btnGuardar?.addEventListener('click', onGuardar);
  btnGuardarBottom?.addEventListener('click', onGuardar);
  tbody?.addEventListener('click', onClickTable);
  tbody?.addEventListener('keydown', onEnterNuevaFila);
})();
