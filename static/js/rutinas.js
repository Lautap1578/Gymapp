// --- INIT SELECT2 ROBUSTO ---
function initSelect2(scope){
  $(scope).find('select.ejercicio-select').each(function(){
    const $sel = $(this);

    // Limpieza FULL por si viene clonada
    $sel.off();
    if ($sel.hasClass('select2-hidden-accessible')) {
      try { $sel.select2('destroy'); } catch(e){}
      $sel.removeClass('select2-hidden-accessible');
      $sel.removeAttr('data-select2-id');
      const $next = $sel.next('.select2');
      if ($next.length) $next.remove();
    }

    // Inicialización fresca
    $sel.select2({
      placeholder: "Seleccionar ejercicio…",
      allowClear: true,
      minimumResultsForSearch: 0,
      width: '100%',
      dropdownParent: $(document.body)
    });
  });
}

// Helpers conteo de filas
function contarFilas(idTabla){ return document.querySelectorAll('#' + idTabla + ' tbody tr').length; }
function actualizarTotal(idTabla, idSpan){
  const total = contarFilas(idTabla);
  document.getElementById(idSpan).textContent = total;
  if (idTabla === 'tablaRutina') document.getElementById('total_filas_input').value = total;
  if (idTabla === 'tablaCalentamiento') document.getElementById('total_filas_calentamiento_input').value = total;
}

// --- AGREGAR FILA SIN ROMPER NOMBRES NI SELECT2 ---
function agregarFila(idTabla, prefix){
  const $tbody = $('#' + idTabla + ' tbody');
  const index = $tbody.find('tr').length;
  const $fila = $tbody.find('tr').first().clone(false); // sin copiar eventos

  $fila.find('input, select').each(function(){
    const el = this;

    // Si es SELECT clonado desde uno con select2, limpiamos
    if (el.tagName === 'SELECT') {
      const $el = $(el);
      if ($el.hasClass('select2-hidden-accessible')) {
        try { $el.select2('destroy'); } catch(e){}
        $el.removeClass('select2-hidden-accessible').removeAttr('data-select2-id');
        const $next = $el.next('.select2');
        if ($next.length) $next.remove();
      }
    }

    // Renombrado correcto
    const partes = el.name.split('_');
    let baseReal;
    if (partes[0] === 'cal' && partes.length >= 3) {
      baseReal = partes[1]; // después de "cal"
    } else {
      baseReal = partes[0];
    }
    el.name = (prefix || '') + baseReal + '_' + index;

    // Reset de valores
    if (el.tagName === 'SELECT'){
      el.selectedIndex = 0;
    } else {
      el.value = '';
    }
  });

  $tbody.append($fila);
  initSelect2($fila); // solo la nueva fila
  actualizarTotal(idTabla, idTabla === 'tablaRutina' ? 'total_filas' : 'total_filas_calentamiento');
}

// --- ELIMINAR FILA ---
function eliminarFila(btn, idTabla){
  const tbody = document.querySelector('#' + idTabla + ' tbody');
  if (tbody.rows.length <= 1) return;
  btn.closest('tr').remove();
  actualizarTotal(idTabla, idTabla === 'tablaRutina' ? 'total_filas' : 'total_filas_calentamiento');
}

// --- EVENTOS INIT ---
document.addEventListener('click', function(e){
  if (!e.target.matches('.btn-add')) return;
  e.preventDefault();
  const btn = e.target.closest('.btn-add');
  agregarFila(btn.getAttribute('data-tabla'), btn.getAttribute('data-prefix') || '');
});

document.addEventListener('DOMContentLoaded', function(){
  initSelect2(document);
  actualizarTotal('tablaCalentamiento','total_filas_calentamiento');
  actualizarTotal('tablaRutina','total_filas');

  // Toggle densidad
  const wrap = document.getElementById("rutina-wrap");
  const comfy = document.getElementById("density-comfy");
  const compact = document.getElementById("density-compact");
  if (comfy) comfy.onclick = ()=> { wrap.classList.add("table-density-comfy"); wrap.classList.remove("table-density-compact"); };
  if (compact) compact.onclick = ()=> { wrap.classList.add("table-density-compact"); wrap.classList.remove("table-density-comfy"); };
});

