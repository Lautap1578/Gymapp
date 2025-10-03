from datetime import date, datetime
import json
import openpyxl
from django.db.models import Q, F, Sum, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction

from .forms import MemberForm, MemberInfoForm, DetalleRutinaFormSet, PaymentForm
from .models import Member, Payment, Ejercicio, Rutina, DetalleRutina, ComentarioRutina

from django.utils import timezone
from django.views.decorators.http import require_POST

from django.urls import reverse
from django.utils.http import urlencode


# === Socios ===

def member_list(request):
    q = (request.GET.get('q') or '').strip()

    # Lista de socios (con tu búsqueda actual)
    members = Member.objects.all().order_by('nombre_apellido')
    if q:
        members = members.filter(
            Q(nombre_apellido__icontains=q) |
            Q(dni__icontains=q) |
            Q(telefono__icontains=q) |
            Q(gmail__icontains=q)
        )

    # Mes actual (día 1)
    today = date.today()
    current_month = today.replace(day=1)

    # IDs de socios con pago del mes actual (pagado=True y no anulado)
    pagos_ids = set(
        Payment.objects.filter(
            mes=current_month,
            pagado=True,
            anulado=False
        ).values_list('member_id', flat=True)
    )

    # Deudores = socios SIN pago del mes actual
    deudores = Member.objects.exclude(id__in=pagos_ids).order_by('nombre_apellido')

    context = {
        'members': members,
        'pagos_ids': pagos_ids,        # lo mantenemos por compatibilidad si lo usás en el template
        'deudores': deudores,          # <<< NUEVO
        'current_month': current_month # <<< NUEVO (para mostrar "Octubre 2025", etc.)
    }
    return render(request, 'gymapp/member_list.html', context)


def add_member(request):
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('member_list')
    else:
        form = MemberForm()
    return render(request, 'gymapp/add_member.html', {'form': form})


def edit_member(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            return redirect('member_list')
    else:
        form = MemberForm(instance=member)
    return render(request, 'gymapp/edit_member.html', {'form': form})


def delete_member(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        member.delete()
        return redirect('member_list')
    return render(request, 'gymapp/confirm_delete.html', {'member': member})


# === Pagos (botón rápido “Debe/Pagado”) ===
@require_POST
def toggle_payment(request, member_id):
    """
    Cambia el estado de pago rápido (Debe/Pagado) para el socio en el mes actual.

    Si no existe un registro de pago para el mes actual, se crea uno con
    `pagado=True`. Si ya existe, se invierte el estado de `pagado`.  Este
    método no toca el campo `anulado` que está reservado para anular pagos
    con plan.  Si se desmarca el pago (pagado=False) no se elimina el
    registro sino que simplemente refleja que ese mes está pendiente.
    """
    member = get_object_or_404(Member, pk=member_id)
    mes_actual = date.today().replace(day=1)
    # Buscar o crear el pago correspondiente al mes
    pago, created = Payment.objects.get_or_create(
        member=member,
        mes=mes_actual,
        defaults={"pagado": True},
    )
    if not created:
        # Alternar el estado de pagado (Debe/Pagado)
        pago.pagado = not pago.pagado
        pago.save(update_fields=["pagado"])
    return redirect('member_list')


def historial_pagos(request, member_id):
    from datetime import date as _date
    member = get_object_or_404(Member, pk=member_id)
    # Cargar pagos de este socio.  Para el historial, consideramos que un mes
    # está pagado solo si existe un Payment con pagado=True y anulado=False.
    pagos = Payment.objects.filter(member=member)

    historial = []
    hoy = _date.today().replace(day=1)
    fecha = member.fecha_alta.replace(day=1)

    while fecha <= hoy:
        mes_str = fecha.strftime("%m-%Y")
        # Determinar si el mes se marca como pagado (no anulado y pagado=True)
        pagado = pagos.filter(mes=fecha, pagado=True, anulado=False).exists()
        historial.append({'mes': mes_str, 'pagado': pagado})
        if fecha.month == 12:
            fecha = fecha.replace(year=fecha.year + 1, month=1)
        else:
            fecha = fecha.replace(month=fecha.month + 1)

    return render(request, 'gymapp/historial_pagos.html', {
        'member': member,
        'historial': historial
    })


@require_POST
def eliminar_pago(request, pago_id):
    """
    Anula un pago (no lo borra). Luego redirige al resumen del mismo mes.
    """
    pago = get_object_or_404(Payment, id=pago_id)
    pago.anulado = True
    pago.save()

    # Volver al mismo mes del resumen
    mes_param = pago.mes.strftime("%Y-%m")
    url = reverse("resumen_mensual")
    return redirect(f"{url}?{urlencode({'mes': mes_param})}")


@require_POST
def toggle_payment_mes(request, member_id, mes):
    """
    Alterna el estado "Pagado/Debe" para un mes específico en el historial.

    Si no existe un pago para ese mes, se crea con pagado=True.  Si ya
    existe, se invierte el estado de `pagado`.  No se toca el campo
    `anulado`, que corresponde a anular un pago con plan.  Este endpoint
    permite que los usuarios marquen y desmarquen rápidamente los pagos
    mensuales en el historial.
    """
    member = get_object_or_404(Member, pk=member_id)
    try:
        mes_date = datetime.strptime(mes, "%m-%Y").date().replace(day=1)
    except Exception:
        mes_date = date.today().replace(day=1)

    pago, created = Payment.objects.get_or_create(
        member=member,
        mes=mes_date,
        defaults={"pagado": True},
    )
    if not created:
        pago.pagado = not pago.pagado
        pago.save(update_fields=["pagado"])
    return redirect('historial_pagos', member_id=member_id)


def export_members_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Socios"

    headers = [
        "Nombre y Apellido", "DNI", "Gmail", "Teléfono", "Dirección", "Edad",
        "Historial Deportivo", "Experiencias Gimnasios", "Historial Lesivo",
        "Enfermedades", "Objetivos", "Frecuencia Semana"
    ]
    ws.append(headers)

    for m in Member.objects.all():
        ws.append([
            m.nombre_apellido or "",
            m.dni or "",
            m.gmail or "",
            m.telefono or "",
            m.direccion or "",
            m.edad or "",
            m.historial_deportivo or "",
            m.experiencias_gimnasios or "",
            m.historial_lesivo or "",
            m.enfermedades or "",
            m.objetivos or "",
            m.frecuencia_semana or ""
        ])

    response = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = 'attachment; filename="socios.xlsx"'
    wb.save(response)
    return response


def login_cliente(request):
    if request.method == "POST":
        dni = request.POST.get("dni", "").strip()
        if not dni:
            messages.warning(request, "Ingresá tu DNI.")
            return redirect("login_cliente")
        try:
            member = Member.objects.get(dni=dni)
            request.session["cliente_id"] = member.id
            messages.success(request, f"Bienvenido, {member.nombre_apellido}.")
            return redirect("mis_rutinas", member.id)
        except Member.DoesNotExist:
            messages.error(request, "DNI no registrado. Verificá los datos.")
            return redirect("login_cliente")
    return render(request, "gymapp/login_cliente.html")


def member_rows_partial(request):
    q = request.GET.get("q") or ""
    members = Member.objects.filter(
        Q(nombre_apellido__icontains=q) |
        Q(gmail__icontains=q) |
        Q(telefono__icontains=q) |
        Q(dni__icontains=q)
    ).order_by("nombre_apellido")

    current_month = date.today().replace(day=1)
    pagos_ids = set(
        p.member_id for p in Payment.objects.filter(
            anulado=False,
            pagado=True,
            mes=current_month,
        )
    )

    return render(request, "gymapp/partials/_member_rows.html", {
        "members": members,
        "pagos_ids": pagos_ids,
        "current_month": current_month,
    })


def update_member_info(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == "POST":
        form = MemberInfoForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
    return redirect('member_list')


# === Rutinas ===

def rutina_cliente(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    rutinas = member.rutinas.order_by("-fecha_creacion")

    if request.method == "POST":
        ultima = rutinas.first()
        if ultima:
            nueva = Rutina.objects.create(member=member, estructura=ultima.estructura)
            detalles = ultima.detalles.select_related("ejercicio").values(
                "categoria", "ejercicio_id", "series", "repeticiones", "peso",
                "descanso", "rir", "sensaciones", "notas", "es_calentamiento",
            )
            DetalleRutina.objects.bulk_create(
                [DetalleRutina(rutina=nueva, **d) for d in detalles]
            )
            if hasattr(ultima, "comentario"):
                ComentarioRutina.objects.create(rutina=nueva, texto=ultima.comentario.texto)
        else:
            estructura = request.POST.get("estructura", "hipertrofia")
            nueva = Rutina.objects.create(member=member, estructura=estructura)
        return redirect("editar_rutina", nueva.id)

    return render(request, "gymapp/rutina_cliente.html", {
        "member": member,
        "rutinas": rutinas
    })



def crear_rutina(request, member_id, tipo):
    import unicodedata
    member = get_object_or_404(Member, id=member_id)
    def _norm(s):
        s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode('ascii')
        return s.lower().strip()
    label = _norm(tipo)
    mapping = {
        "hipertrofia": "hipertrofia",
        "acondicionamiento fisico": "acondicionamiento",
        "deportista avanzado": "deportista",
        "iniciacion": "iniciacion",
        "edad temprana": "iniciacion",
        "fuerza base": "fuerza_base",
    }
    clave = mapping.get(label, "fuerza_base")
    Rutina.objects.create(member=member, estructura=clave)
    return redirect("rutina_cliente", member_id=member.id)


def editar_rutina(request, rutina_id):
    """
    Render de edición. Mantiene compatibilidad con POST por formset (flujo viejo)
    y en GET arma 'filas' para el nuevo template con tabla editable.
    """
    rutina = get_object_or_404(Rutina, pk=rutina_id)
    ejercicios = Ejercicio.objects.all().order_by("nombre")
    categorias = [
        "Pectorales", "Espalda", "Deltoides", "Bíceps", "Tríceps",
        "Cuádriceps", "Isquiotibiales", "Pantorrilla", "Abdomen",
        "Trapecios", "Antebrazos"
    ]

    # === Flujo viejo (formset) ===
    if request.method == "POST":
        detalles_data = []
        filas_c = int(request.POST.get("total_filas_calentamiento", 0))
        for i in range(filas_c):
            detalles_data.append({
                "categoria": request.POST.get(f"cal_categoria_{i}", ""),
                "ejercicio": request.POST.get(f"cal_ejercicio_{i}") or None,
                "repeticiones": request.POST.get(f"cal_repeticiones_{i}", ""),
                "descanso": request.POST.get(f"cal_descanso_{i}", ""),
                "notas": request.POST.get(f"cal_notas_{i}", ""),
                "es_calentamiento": True,
            })

        filas = int(request.POST.get("total_filas", 0))
        for i in range(filas):
            detalles_data.append({
                "categoria": request.POST.get(f"categoria_{i}", ""),
                "ejercicio": request.POST.get(f"ejercicio_{i}") or None,
                "series": request.POST.get(f"series_{i}", ""),
                "repeticiones": request.POST.get(f"repeticiones_{i}", ""),
                "peso": request.POST.get(f"peso_{i}", ""),
                "descanso": request.POST.get(f"descanso_{i}", ""),
                "rir": request.POST.get(f"rir_{i}", ""),
                "sensaciones": request.POST.get(f"sensaciones_{i}", ""),
                "notas": request.POST.get(f"notas_{i}", ""),
                "es_calentamiento": False,
            })

        formset_data = {
            "detalles-TOTAL_FORMS": str(len(detalles_data)),
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "0",
            "detalles-MAX_NUM_FORMS": "1000",
        }
        for i, detalle in enumerate(detalles_data):
            for campo, valor in detalle.items():
                formset_data[f"detalles-{i}-{campo}"] = valor

        formset = DetalleRutinaFormSet(formset_data, instance=rutina, prefix="detalles")

        if formset.is_valid():
            with transaction.atomic():
                # Al crear una nueva versión, preservamos la semana de la rutina
                # original para que la información de semana no se pierda al
                # versionar mediante el flujo antiguo (formset).
                nueva = Rutina.objects.create(
                    member=rutina.member,
                    estructura=rutina.estructura,
                    semana=getattr(rutina, "semana", 1),
                )
                nuevos = []
                for form in formset.forms:
                    if form.cleaned_data:
                        data = form.cleaned_data.copy()
                        data.pop("rutina", None)
                        nuevos.append(DetalleRutina(rutina=nueva, **data))
                if nuevos:
                    DetalleRutina.objects.bulk_create(nuevos)

                texto = request.POST.get("comentario", "")
                if not texto and hasattr(rutina, "comentario"):
                    texto = rutina.comentario.texto
                if texto:
                    ComentarioRutina.objects.create(rutina=nueva, texto=texto)

                messages.success(request, "Se creó una nueva versión de la rutina.")
            return redirect("rutina_cliente", rutina.member.id)
        else:
            messages.error(request, "Revisá los datos: hay campos inválidos o incompletos.")

    # === GET: armar contexto para el template nuevo ===
    filas_ctx = []
    for d in rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"):
        filas_ctx.append({
            "id": d.id,
            "ejercicio_id": d.ejercicio_id or "",
            "series": d.series or "",
            "reps": d.repeticiones or "",
            "kilos": d.peso or "",
            # Incluir campo RIR (Rate of Perceived Exertion inverso) en el contexto
            "rir": d.rir or "",
            "notas": d.notas or "",
        })

    # Construcción de la lista de semanas (por defecto 1..8).  El valor
    # seleccionado por defecto se obtiene de la propia rutina si posee la
    # propiedad ``semana`` definida; de lo contrario se usa 1.  Esto mejora la
    # experiencia al mantener la semana elegida al crear nuevas versiones.
    semanas = [{"id": i, "numero": i} for i in range(1, 9)]  # 1..8
    semana_activa_id = getattr(rutina, "semana", 1) or 1
    vista_por_semanas = False

    contexto = {
        "rutina": rutina,
        "ejercicios": ejercicios,
        "categorias": categorias,
        # compat con template viejo
        "detalles": rutina.detalles.filter(es_calentamiento=False),
        "calentamiento": rutina.detalles.filter(es_calentamiento=True),
        "comentario": getattr(rutina, "comentario", None),
        # usado por el template nuevo
        "filas": filas_ctx,
        "semanas": semanas,
        "semana_activa_id": semana_activa_id,
        "vista_por_semanas": vista_por_semanas,
    }

    # --- Soporte para estructura "Fuerza base" ---
    # Si la rutina es de tipo fuerza_base, armamos un contexto adicional con
    # 2 secciones: "Parte Inicial" (calentamiento) y "Parte Principal" (4
    # grupos musculares predefinidos).  Cada detalle de la rutina se
    # clasifica como calentamiento (es_calentamiento=True) o principal.
    if rutina.estructura == "fuerza_base":
        # Construir filas para el calentamiento: un dict por fila con las
        # mismas claves que el nuevo front.  Si no hay registros, se
        # devuelve una lista vacía para que el front genere 3 filas por
        # defecto.
        filas_cal = []
        for d in rutina.detalles.filter(es_calentamiento=True).select_related("ejercicio"):
            filas_cal.append({
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                "rir": d.rir or "",
                "notas": d.notas or "",
            })

        # Definir las categorías predeterminadas para la parte principal.
        categorias_fb = [
            "Cadena anterior",
            "Tracciones",
            "Cadena posterior",
            "Empujes",
        ]
        filas_principal = []
        # Creamos un mapa para acceder rápidamente al primer detalle por
        # categoría.  Esto asegura que si existen múltiples ejercicios bajo
        # la misma categoría (caso excepcional), solo se considere el
        # primero.
        detalles_por_cat = {}
        for d in rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"):
            cat = d.categoria or ""
            # Normalizar categoría: se compara de forma insensible a mayúsculas
            # para evitar duplicados causados por diferencias de capitalización.
            cat_key = cat.strip().lower()
            if cat_key and cat_key not in detalles_por_cat:
                detalles_por_cat[cat_key] = d

        for cat in categorias_fb:
            key = cat.strip().lower()
            det = detalles_por_cat.get(key)
            filas_principal.append({
                "categoria": cat,
                "ejercicio_id": det.ejercicio_id or "" if det else "",
                "series": det.series or "" if det else "",
                "reps": det.repeticiones or "" if det else "",
                "kilos": det.peso or "" if det else "",
                "rir": det.rir or "" if det else "",
                "notas": det.notas or "" if det else "",
            })

        contexto.update({
            "filas_calentamiento": filas_cal,
            "filas_principal": filas_principal,
        })
        return render(request, "gymapp/editar_rutina_fuerza_base.html", contexto)

    elif rutina.estructura == "acondicionamiento":
        # Estructura similar a Fuerza base, pero sin columna RIR
        # y con un grupo adicional en la parte principal: "Variabilidad de movimiento".
        # Calentamiento
        filas_cal = []
        for d in rutina.detalles.filter(es_calentamiento=True).select_related("ejercicio"):
            filas_cal.append({
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                # "rir" intencionalmente omitido en UI; igual si viene se ignora
                "notas": d.notas or "",
            })
        if not filas_cal:
            filas_cal = [{"id": None, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "notas": ""} for _ in range(3)]

        # Parte principal con categorías sugeridas
        categorias_ac = [
            "Cadena anterior",
            "Tracciones",
            "Cadena posterior",
            "Empujes",
            "Variabilidad de movimiento",
        ]

        filas_principal = []
        detalles_por_cat = {}
        for d in rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"):
            cat = (d.categoria or "").strip()
            key = cat.lower()
            if key and key not in detalles_por_cat:
                detalles_por_cat[key] = d

        for cat in categorias_ac:
            key = cat.strip().lower()
            det = detalles_por_cat.get(key)
            if det:
                filas_principal.append({
                    "id": det.id,
                    "categoria": cat,
                    "ejercicio_id": det.ejercicio_id or "",
                    "series": det.series or "",
                    "reps": det.repeticiones or "",
                    "kilos": det.peso or "",
                    "notas": det.notas or "",
                })
            else:
                filas_principal.append({
                    "id": None,
                    "categoria": cat,
                    "ejercicio_id": "",
                    "series": "",
                    "reps": "",
                    "kilos": "",
                    "notas": "",
                })

        contexto.update({
            "filas_calentamiento": filas_cal,
            "filas_principal": filas_principal,
        })
        return render(request, "gymapp/editar_rutina_acondicionamiento.html", contexto)
    
    elif rutina.estructura == "iniciacion":
        # Iniciación: igual a acondicionamiento pero con:
        # - Parte inicial: exactamente 5 ejercicios
        # - Parte principal: exactamente 2 ejercicios (sin columna de categoría/grupo)
        filas_cal = []
        for d in rutina.detalles.filter(es_calentamiento=True).select_related("ejercicio"):
            filas_cal.append({
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                "rir": d.rir or "",
                "notas": d.notas or "",
            })
        # Forzar 5 filas
        if len(filas_cal) < 5:
            for _ in range(5 - len(filas_cal)):
                filas_cal.append({"id": None, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "rir": "", "notas": ""})
        else:
            filas_cal = filas_cal[:5]

        filas_principal = []
        existentes = list(rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"))[:2]
        for d in existentes:
            filas_principal.append({
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                "rir": d.rir or "",
                "notas": d.notas or "",
            })
        # Completar hasta 2
        while len(filas_principal) < 2:
            filas_principal.append({"id": None, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "rir": "", "notas": ""})

        contexto.update({
            "filas_calentamiento": filas_cal,
            "filas_principal": filas_principal,
        })
        return render(request, "gymapp/editar_rutina_iniciacion.html", contexto)
    elif rutina.estructura == "deportista":
        # Parte inicial: siempre 3 ejercicios
        filas_cal = []
        for d in rutina.detalles.filter(es_calentamiento=True).select_related("ejercicio"):
            filas_cal.append({
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                "notas": d.notas or "",
            })
        while len(filas_cal) < 3:
            filas_cal.append({"id": None, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "notas": ""})

        # Bloque 1 — Fuerza: 1 ejercicio por grupo fijo
        grupos_fuerza = ["Cadena anterior", "Cadena posterior", "Empujes o Tracciones"]
        filas_fuerza = []
        existentes = {}
        for d in rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"):
            key = (d.categoria or "").strip().lower()
            existentes.setdefault(key, []).append(d)
        for cat in grupos_fuerza:
            key = cat.strip().lower()
            det = existentes.get(key, [None])[0]
            if det:
                filas_fuerza.append({
                    "id": det.id,
                    "categoria": cat,
                    "ejercicio_id": det.ejercicio_id or "",
                    "series": det.series or "",
                    "reps": det.repeticiones or "",
                    "kilos": det.peso or "",
                    "notas": det.notas or "",
                })
            else:
                filas_fuerza.append({
                    "id": None,
                    "categoria": cat,
                    "ejercicio_id": "",
                    "series": "",
                    "reps": "",
                    "kilos": "",
                    "notas": "",
                })

        # Bloque 2 — Potencia: 3..6 (arranca con 3)
        filas_potencia = []
        while len(filas_potencia) < 3:
            filas_potencia.append({"id": None, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "notas": ""})

        # Bloque 3 — Accesorios: 3..6 (arranca con 3)
        filas_accesorios = []
        while len(filas_accesorios) < 3:
            filas_accesorios.append({"id": None, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "notas": ""})

        contexto.update({
            "filas_calentamiento": filas_cal,
            "filas_fuerza": filas_fuerza,
            "filas_potencia": filas_potencia,
            "filas_accesorios": filas_accesorios,
        })
        return render(request, "gymapp/editar_rutina_deportista.html", contexto)

    return render(request, "gymapp/editar_rutina.html", contexto)

@require_POST
def guardar_rutina(request, rutina_id):
    """
    Recibe 'payload' JSON desde el nuevo front (tabla editable) y crea
    una NUEVA versión de la rutina (mismo criterio que en editar_rutina).
    Estructura esperada:
    {
      "semana_id": "1",
      "filas": [
        {"ejercicio_id": "3", "series": "3", "reps": "8-10", "kilos": "40", "notas": "RIR 1-2"},
        ...
      ]
    }
    """
    rutina = get_object_or_404(Rutina, pk=rutina_id)

    payload = request.POST.get("payload", "")
    try:
        data = json.loads(payload) if payload else {"filas": []}
    except json.JSONDecodeError:
        messages.error(request, "No se pudo leer el formato enviado. Reintentá.")
        return redirect("editar_rutina", rutina_id)

    filas = data.get("filas", []) or []

    with transaction.atomic():
        # versionado: nueva rutina.  Se preserva o actualiza el número de semana
        # que viene desde el front (payload) para que la información sea
        # persistente en la base de datos.  Si no se envía, se toma la
        # semana de la rutina original o 1 por defecto.
        semana_str = data.get("semana_id") or request.POST.get("semana_id")
        try:
            semana_id = int(semana_str)
        except (TypeError, ValueError):
            semana_id = getattr(rutina, "semana", 1)

        nueva = Rutina.objects.create(
            member=rutina.member,
            estructura=rutina.estructura,
            semana=semana_id or 1,
        )

        nuevos = []
        for f in filas:
            ej_id = f.get("ejercicio_id") or f.get("ejercicio")
            ej = Ejercicio.objects.filter(id=ej_id).first() if ej_id else None
            categoria = f.get("categoria", "") or ""
            # Convertir es_calentamiento a booleano.  Puede venir como
            # cadena "true"/"false", entero 0/1 o valor booleano.
            es_cal = f.get("es_calentamiento", False)
            if isinstance(es_cal, str):
                es_cal = es_cal.lower() in ("1", "true", "t", "yes")
            else:
                es_cal = bool(es_cal)
            nuevos.append(DetalleRutina(
                rutina=nueva,
                categoria=categoria,
                ejercicio=ej,
                series=f.get("series", "") or "",
                repeticiones=f.get("reps", "") or "",
                peso=f.get("kilos", "") or "",
                descanso="",  # opcional
                rir=f.get("rir", "") or "",
                sensaciones="",  # opcional
                notas=f.get("notas", "") or "",
                es_calentamiento=es_cal,
            ))

        if nuevos:
            DetalleRutina.objects.bulk_create(nuevos)

        # copiar comentario previo si existía
        if hasattr(rutina, "comentario") and rutina.comentario and rutina.comentario.texto:
            ComentarioRutina.objects.create(rutina=nueva, texto=rutina.comentario.texto)

    messages.success(request, "Se creó una nueva versión de la rutina.")
    return redirect("rutina_cliente", rutina.member.id)


def eliminar_rutina(request, rutina_id):
    rutina = get_object_or_404(Rutina, id=rutina_id)
    member_id = rutina.member.id
    nombre = rutina.get_estructura_display()
    rutina.delete()
    messages.success(request, f"La rutina '{nombre}' fue eliminada con éxito ✅")
    return redirect('rutina_cliente', member_id=member_id)


def mis_rutinas(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    rutinas = member.rutinas.order_by("-fecha_creacion")

    rutina_data = {}
    for rutina in rutinas:
        data = list(
            rutina.detalles.all().values(
                "categoria", "series", "repeticiones", "peso", "descanso",
                "rir", "sensaciones", "notas", ejercicio=F("ejercicio__nombre"),
            )
        )
        rutina_data[str(rutina.id)] = data

    rutina_data = json.dumps(rutina_data)

    return render(request, "gymapp/mis_rutinas.html", {
        "member": member,
        "rutinas": rutinas,
        "rutina_data": rutina_data,
    })


