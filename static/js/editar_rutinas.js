
// editar_rutinas.js — compatible con inputs de texto o selects.
// Lee tablas por IDs y arma payload unificado.

(function() {
  function val(el, name){
    const n = el.querySelector(name);
    return n ? (n.value || '') : '';
  }
  function readRowsByTableId(tableId, opts){
    const t = document.getElementById(tableId);
    if (!t) return [];
    const out = [];
    t.querySelectorAll('tbody tr').forEach(tr => {
      const data = {
        id: tr.getAttribute('data-id') || null,
        categoria: tr.getAttribute('data-categoria') || '',
        bloque: tr.getAttribute('data-bloque') || (opts && opts.bloque) || '',
        es_calentamiento: tr.hasAttribute('data-cal'),
      };
      // Soportar select o input texto
      const sel = tr.querySelector('select[name="ejercicio"]');
      const txt = tr.querySelector('input[name="ejercicio_txt"]');
      data.ejercicio_id = sel ? (sel.value || '') : '';
      data.ejercicio_txt = txt ? (txt.value || '').trim() : '';

      data.series = val(tr, 'input[name="series"]');
      data.reps   = val(tr, 'input[name="reps"]');
      data.kilos  = val(tr, 'input[name="kilos"]');
      data.notas  = val(tr, 'textarea[name="notas"]');
      data.rir    = val(tr, 'input[name="rir"]'); // opcional

      out.push(data);
    });
    return out;
  }

  /**
   * Construye un payload unificado para enviar al servidor.
   *
   * La aplicación soporta tanto rutinas con múltiples días (cada uno contenido
   * dentro de un elemento .dia-card) como rutinas simples con una única tabla.
   * Este método detecta la estructura del DOM y extrae las filas de manera
   * consistente. Las filas se serializan en una lista llamada `filas`. Cada
   * fila incluye su número de día (`dia`), un flag `es_calentamiento` y los
   * campos correspondientes (categoría, serie, repeticiones, kilos, RIR, etc.).
   *
   * El servidor (guardar_rutina) maneja actualmente dos formatos de datos:
   *   - data.dias: para nuevas interfaces que agrupan filas por día
   *   - data.filas: formato legado con un único día
   *
   * Aquí optamos por generar siempre `filas` con el número de día, ya que el
   * backend contempla este formato y así se mantiene compatibilidad con las
   * versiones anteriores. De esta manera se evita la pérdida de información
   * cuando existen varios días, ya que cada fila contiene su día.
   */
  function buildPayload() {
    const filas = [];

    // Helper para leer valores de inputs/textarea de una fila
    function getVal(row, selector) {
      const el = row.querySelector(selector);
      return el ? (el.value || '') : '';
    }

    // Helper para construir un objeto de detalle a partir de una fila (<tr>)
    function parseRow(row, dia) {
      const detalle = {};
      detalle.dia = dia || 1;
      // Obtener la categoría si está definida en data-attributes.
      detalle.categoria = row.getAttribute('data-categoria') || row.getAttribute('data-bloque') || '';
      // Determinar si es calentamiento: marcado explícitamente en data-cal o
      // inferido del contexto (tabla de calentamiento/inicial). Este flag
      // influye en el orden de presentación de la rutina.
      const tbl = row.closest('table');
      const tblId = tbl ? (tbl.id || '') : '';
      let esCal = false;
      // filas con data-cal="1"
      if (row.hasAttribute('data-cal')) esCal = true;
      // tablas de calentamiento/inicial suelen contener "cal" o "inicial"
      if (!esCal && (tblId.includes('cal') || tblId.includes('inicial'))) esCal = true;
      // algunas filas pasan el bloque a través de data-bloque
      const bloque = row.getAttribute('data-bloque') || '';
      if (!esCal && bloque.toLowerCase().includes('cal')) esCal = true;
      detalle.es_calentamiento = esCal;

      // Leer identificadores de ejercicio. Si hay un select de ejercicios
      // usamos su value; caso contrario puede haber un campo de texto libre.
      const sel = row.querySelector('select[name="ejercicio"]');
      const txt = row.querySelector('input[name="ejercicio_txt"]');
      detalle.ejercicio_id = sel ? (sel.value || '') : '';
      // Algunos formatos incluyen la clave "ejercicio"; mantenemos ambos nombres
      detalle.ejercicio = detalle.ejercicio_id;
      detalle.ejercicio_txt = txt ? (txt.value || '').trim() : '';

      // Mapear los campos de intensidad/volumen
      detalle.series = getVal(row, 'input[name="series"]');
      detalle.reps   = getVal(row, 'input[name="reps"]');
      // En el formulario usamos "kilos"; el backend espera "kilos" para
      // cargar el campo "peso".
      detalle.kilos  = getVal(row, 'input[name="kilos"]');
      detalle.descanso = getVal(row, 'input[name="descanso"]');
      detalle.rir    = getVal(row, 'input[name="rir"]');
      detalle.sensaciones = getVal(row, 'input[name="sensaciones"]');
      // Notas puede estar en textarea
      detalle.notas  = getVal(row, 'textarea[name="notas"]');
      return detalle;
    }

    // Primero: detectar si existen múltiples días. Los días se contienen en
    // elementos con clase .dia-card bajo #daysContainer. Si existen,
    // procesamos cada uno y asignamos su índice como número de día.
    const daysContainer = document.getElementById('daysContainer');
    if (daysContainer) {
      const diaCards = daysContainer.querySelectorAll(':scope > .dia-card');
      if (diaCards.length > 0) {
        diaCards.forEach((card, idx) => {
          const diaNumero = idx + 1;
          // Dentro de cada día recogemos TODAS las tablas (<table>) y sus filas.
          const tables = card.querySelectorAll('table');
          tables.forEach(tbl => {
            const rows = tbl.querySelectorAll('tbody tr');
            rows.forEach(row => {
              // No agregar filas totalmente vacías
              const detalle = parseRow(row, diaNumero);
              // Verificar que tenga al menos algún valor significativo
              const valores = [
                detalle.categoria,
                detalle.series,
                detalle.reps,
                detalle.kilos,
                detalle.rir,
                detalle.notas,
                detalle.ejercicio_txt,
                detalle.ejercicio_id
              ];
              const todosVacios = valores.every(v => !v || (String(v).trim() === ''));
              if (!todosVacios) filas.push(detalle);
            });
          });
        });
        return { filas };
      }
    }
    // Segundo: si no hay estructura de días, intentar leer tablas por ID.
    // Esto mantiene compatibilidad con las plantillas antiguas que usan
    // identificadores fijos como tabla-cal y tabla-principal. Las filas se
    // registran con dia = 1.
    let cal       = readRowsByTableId('tabla-cal',       {bloque:'calentamiento'}) || [];
    let fuerza    = readRowsByTableId('tabla-fuerza',    {bloque:'fuerza'}) || [];
    let potencia  = readRowsByTableId('tabla-potencia',  {bloque:'potencia'}) || [];
    let accesorios= readRowsByTableId('tabla-accesorios',{bloque:'accesorios'}) || [];
    // Compat Acond/Fuerza base: buscar IDs alternativos
    if (cal.length === 0)       cal = readRowsByTableId('tabla-calentamiento', {bloque:'calentamiento'}) || [];
    if (fuerza.length === 0)    fuerza = readRowsByTableId('tabla-principal',  {bloque:'principal'}) || [];
    const detalles = [].concat(cal, fuerza, potencia, accesorios);
    detalles.forEach(det => {
      // Asegurar que cada registro tenga la clave dia
      det.dia = 1;
      // Normalizar campos vacíos
      det.descanso = det.descanso || '';
      det.sensaciones = det.sensaciones || '';
      // No incluir registros totalmente vacíos
      const valores = [
        det.categoria,
        det.series,
        det.reps,
        det.kilos,
        det.rir,
        det.notas,
        det.ejercicio_txt,
        det.ejercicio_id
      ];
      const vacio = valores.every(v => !v || (String(v).trim() === ''));
      if (!vacio) filas.push(det);
    });
    return { filas };
  }

  function onGuardarClick(e) {
    e && e.preventDefault();
    const payloadInput = document.getElementById('payload_input');
    if (!payloadInput) { alert('No se encontró el input oculto payload_input'); return; }
    const semana = document.getElementById('semana-select');
    const data = buildPayload();
    data.semana_id = semana ? (semana.value || '') : '';

    payloadInput.value = JSON.stringify(data);
    const form = document.getElementById('form-guardar');
    if (!form) { alert('No se encontró el form de guardado'); return; }
    form.submit();
  }

  function wire(){
    [document.getElementById('btn-guardar'), document.getElementById('btn-guardar-bottom')]
      .forEach(b => b && b.addEventListener('click', onGuardarClick));
  }

  document.addEventListener('DOMContentLoaded', wire);
})();
