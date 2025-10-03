
// editar_rutinas.js — unifica guardado para múltiples bloques (cal/fuerza/potencia/accesorios)
// Mantiene compatibilidad con plantillas anteriores (Fuerza base, Acondicionamiento).

(function() {
  function readTableRows(tableId, opts) {
    var table = document.getElementById(tableId);
    if (!table) return [];
    var rows = table.querySelectorAll('tbody tr');
    var out = [];
    rows.forEach(function(tr) {
      var data = {
        id: tr.getAttribute('data-id') || null,
        categoria: tr.getAttribute('data-categoria') || '',
        bloque: tr.getAttribute('data-bloque') || (opts && opts.bloque) || '',
        es_calentamiento: tr.hasAttribute('data-cal')
      };
      var sel = tr.querySelector('select[name="ejercicio"]');
      var series = tr.querySelector('input[name="series"]');
      var reps = tr.querySelector('input[name="reps"]');
      var kilos = tr.querySelector('input[name="kilos"]');
      var notas = tr.querySelector('textarea[name="notas"]');

      data.ejercicio_id = sel ? (sel.value || '') : '';
      data.series = series ? (series.value || '') : '';
      data.reps = reps ? (reps.value || '') : '';
      data.kilos = kilos ? (kilos.value || '') : '';
      data.notas = notas ? (notas.value || '') : '';

      // RIR es opcional (no usado en algunas vistas)
      var rir = tr.querySelector('input[name="rir"]');
      data.rir = rir ? (rir.value || '') : '';

      out.push(data);
    });
    return out;
  }

  function buildPayload() {
    // Compatibilidad: si existe una sola tabla estándar (e.g., fuerza_base)
    var single = document.querySelector('#tabla-principal, #tabla-calentamiento');
    // Nuevos IDs para Deportista Avanzado
    var cal = readTableRows('tabla-cal', { bloque: 'calentamiento' });
    var fuerza = readTableRows('tabla-fuerza', { bloque: 'fuerza' });
    var potencia = readTableRows('tabla-potencia', { bloque: 'potencia' });
    var accesorios = readTableRows('tabla-accesorios', { bloque: 'accesorios' });

    // Fallback a IDs previos
    if (cal.length === 0) cal = readTableRows('tabla-calentamiento', { bloque: 'calentamiento' });
    if (fuerza.length === 0) fuerza = readTableRows('tabla-principal', { bloque: 'principal' });

    var all = [].concat(cal, fuerza, potencia, accesorios);

    // Si no hay nuevas tablas, recolectar genérico (compatibilidad)
    if (all.length === 0 && single) {
      all = [].concat(
        readTableRows('tabla-calentamiento', { bloque: 'calentamiento' }),
        readTableRows('tabla-principal', { bloque: 'principal' })
      );
    }

    return { detalles: all };
  }

  function onGuardarClick(e) {
    e && e.preventDefault();
    var payloadInput = document.getElementById('payload_input');
    if (!payloadInput) {
      alert('No se encontró el input oculto payload_input');
      return;
    }
    var data = buildPayload();
    payloadInput.value = JSON.stringify(data);
    var form = document.getElementById('form-guardar');
    if (!form) {
      alert('No se encontró el form de guardado');
      return;
    }
    form.submit();
  }

  function wireButtons() {
    var btns = [document.getElementById('btn-guardar'), document.getElementById('btn-guardar-bottom')];
    btns.forEach(function(b) { if (b) b.addEventListener('click', onGuardarClick); });
  }

  // Inicializar
  document.addEventListener('DOMContentLoaded', wireButtons);
})();
