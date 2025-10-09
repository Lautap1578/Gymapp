from datetime import date, datetime
import json
import openpyxl
from django.db.models import Q, Prefetch
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction

from .forms import (
    MemberForm,
    MemberInfoForm,
    DetalleRutinaFormSet,
    DetalleRutinaPayloadForm,
)
from .models import Member, Payment, Ejercicio, Rutina, DetalleRutina, ComentarioRutina

from django.views.decorators.http import require_POST


# === Socios ===

def member_list(request):
    q = (request.GET.get('q') or '').strip()

    members = Member.objects.all().order_by('nombre_apellido')
    if q:
        members = members.filter(
            Q(nombre_apellido__icontains=q) |
            Q(dni__icontains=q) |
            Q(telefono__icontains=q) |
            Q(gmail__icontains=q)
        )

    today = date.today()
    current_month = today.replace(day=1)

    pagos_ids = set(
        Payment.objects.filter(
            mes=current_month,
            pagado=True,
            anulado=False
        ).values_list('member_id', flat=True)
    )

    deudores = Member.objects.exclude(id__in=pagos_ids).order_by('nombre_apellido')

    context = {
        'members': members,
        'pagos_ids': pagos_ids,
        'deudores': deudores,
        'current_month': current_month
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
    member = get_object_or_404(Member, pk=member_id)
    mes_actual = date.today().replace(day=1)
    pago, created = Payment.objects.get_or_create(
        member=member,
        mes=mes_actual,
        defaults={"pagado": True},
    )
    if not created:
        pago.pagado = not pago.pagado
        pago.save(update_fields=["pagado"])
    return redirect('member_list')


def historial_pagos(request, member_id):
    from datetime import date as _date
    member = get_object_or_404(Member, pk=member_id)
    pagos_realizados = Payment.objects.filter(
        member=member,
        pagado=True,
        anulado=False,
    ).values_list('mes', flat=True)
    meses_pagados = {
        mes.replace(day=1)
        for mes in pagos_realizados
        if mes is not None
    }

    historial = []
    hoy = _date.today().replace(day=1)
    fecha = member.fecha_alta.replace(day=1)

    while fecha <= hoy:
        mes_str = fecha.strftime("%m-%Y")
        pagado = fecha in meses_pagados
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
    pago = get_object_or_404(Payment, id=pago_id)
    pago.anulado = True
    pago.save()
    return redirect("historial_pagos", member_id=pago.member_id)


@require_POST
def toggle_payment_mes(request, member_id, mes):
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
    rutinas = member.rutinas.order_by("-fecha_creacion").prefetch_related(
        "detalles__ejercicio",
        "comentario",
    )

    if request.method == "POST":
        ultima = rutinas.first()
        if ultima:
            nueva = Rutina.objects.create(
                member=member,
                estructura=ultima.estructura,
                semana=ultima.semana,
            )
            detalles = ultima.detalles.select_related("ejercicio").values(
                "dia", "categoria", "ejercicio_id", "series", "repeticiones", "peso",
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
    Editor de rutinas. Para fuerza_base ahora soporta múltiples DÍAS (día = parte inicial + parte principal).
    Mantiene compatibilidad con el flujo viejo (formset) y otras estructuras.
    """
    rutina = get_object_or_404(Rutina, pk=rutina_id)
    ejercicios = Ejercicio.objects.all().order_by("nombre")
    categorias = [
        "Pectorales", "Espalda", "Deltoides", "Bíceps", "Tríceps",
        "Cuádriceps", "Isquiotibiales", "Pantorrilla", "Abdomen",
        "Trapecios", "Antebrazos"
    ]

    # === Flujo viejo (formset) ===
    if request.method == "POST" and "detalles-TOTAL_FORMS" in request.POST:
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
                        # flujo viejo => asignar día=1
                        nuevos.append(DetalleRutina(rutina=nueva, dia=1, **data))
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

    # === GET: armar contexto ===
    # Estructura por defecto para fuerza_base (categorías sugeridas)
    categorias_fb = ["Cadena anterior", "Tracciones", "Cadena posterior", "Empujes"]

    # Si la rutina es fuerza_base, agrupar por día
    if rutina.estructura == "fuerza_base":
        # Traer detalles ordenados por dia para que el front preserve el orden visual
        detalles = rutina.detalles.select_related("ejercicio").order_by("dia", "id")

        # Detectar cuántos días hay; si no hay datos, un día por defecto
        dias_ids = sorted(set(d.detalle_rutina.dia for d in []) )  # dummy para claridad
        dias_map = {}
        max_dia = 1
        for d in detalles:
            dia = d.dia or 1
            max_dia = max(max_dia, dia)
            dias_map.setdefault(dia, {"calentamiento": [], "principal": []})
            fila = {
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                "rir": d.rir or "",
                "notas": d.notas or "",
            }
            if d.es_calentamiento:
                dias_map[dia]["calentamiento"].append(fila)
            else:
                fila_p = fila.copy()
                fila_p["categoria"] = d.categoria or ""
                dias_map[dia]["principal"].append(fila_p)

        # Si no había datos, crear un día 1 base con las 4 categorías en blanco
        if not dias_map:
            dias_map[1] = {
                "calentamiento": [],
                "principal": [{"categoria": c, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "rir": "", "notas": ""} for c in categorias_fb]
            }

        # Normalizar: en principal permitimos múltiples filas y la categoría se elige en un <select>
        dias = []
        for dia_idx in sorted(dias_map.keys()):
            cal = dias_map[dia_idx]["calentamiento"]
            pr = dias_map[dia_idx]["principal"]
            # Si no hay principal, al menos ofrecer 4 filas base con categorías sugeridas
            if not pr:
                pr = [{"categoria": c, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "rir": "", "notas": ""} for c in categorias_fb]
            dias.append({
                "numero": dia_idx,
                "calentamiento": cal,
                "principal": pr
            })

        semanas = [{"id": i, "numero": i} for i in range(1, 9)]
        semana_activa_id = getattr(rutina, "semana", 1) or 1

        contexto = {
            "rutina": rutina,
            "ejercicios": ejercicios,
            "categorias": categorias_fb,
            "dias": dias,  # <<< NUEVO
            "semanas": semanas,
            "semana_activa_id": semana_activa_id,
            "vista_por_semanas": False,
        }
        return render(request, "gymapp/editar_rutina_fuerza_base.html", contexto)

    # === Otras estructuras tal como estaban ===
    # (Recorte: mantenemos los bloques de acondicionamiento, iniciación y deportista
    # igual que tu archivo anterior)
    # ------------------------------------------------------------------------------

    # --- Acondicionamiento ---
    if rutina.estructura == "acondicionamiento":
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
        if not filas_cal:
            filas_cal = [{"id": None, "ejercicio_id": "", "series": "", "reps": "", "kilos": "", "notas": ""} for _ in range(3)]

        categorias_ac = ["Cadena anterior", "Tracciones", "Cadena posterior", "Empujes", "Variabilidad de movimiento"]

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

        semanas = [{"id": i, "numero": i} for i in range(1, 9)]
        semana_activa_id = getattr(rutina, "semana", 1) or 1

        contexto = {
            "rutina": rutina,
            "ejercicios": ejercicios,
            "filas_calentamiento": filas_cal,
            "filas_principal": filas_principal,
            "semanas": semanas,
            "semana_activa_id": semana_activa_id,
        }
        return render(request, "gymapp/editar_rutina_acondicionamiento.html", contexto)

    # (iniciación y deportista quedan como los tenías)

    # Fallback
    filas_ctx = []
    for d in rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"):
        filas_ctx.append({
            "id": d.id,
            "ejercicio_id": d.ejercicio_id or "",
            "series": d.series or "",
            "reps": d.repeticiones or "",
            "kilos": d.peso or "",
            "rir": d.rir or "",
            "notas": d.notas or "",
        })

    semanas = [{"id": i, "numero": i} for i in range(1, 9)]
    semana_activa_id = getattr(rutina, "semana", 1) or 1
    vista_por_semanas = False

    contexto = {
        "rutina": rutina,
        "ejercicios": ejercicios,
        "categorias": categorias,
        "detalles": rutina.detalles.filter(es_calentamiento=False),
        "calentamiento": rutina.detalles.filter(es_calentamiento=True),
        "comentario": getattr(rutina, "comentario", None),
        "filas": filas_ctx,
        "semanas": semanas,
        "semana_activa_id": semana_activa_id,
        "vista_por_semanas": vista_por_semanas,
    }
    return render(request, "gymapp/editar_rutina.html", contexto)


@require_POST
def guardar_rutina(request, rutina_id):
    """
    Nuevo payload soportado (compat con el viejo):
    - NUEVO:
      {
        "semana_id": "1",
        "dias": [
          {
            "calentamiento": [ {ejercicio_id, series, reps, kilos, rir, notas}, ... ],
            "principal":     [ {categoria, ejercicio_id, series, reps, kilos, rir, notas}, ... ]
          },
          ...
        ]
      }
    - VIEJO:
      { "semana_id": "1", "filas": [ ... ], "es_calentamiento": bool, "categoria": "" }
    """
    rutina = get_object_or_404(Rutina, pk=rutina_id)

    payload = request.POST.get("payload", "")
    try:
        data = json.loads(payload) if payload else {}
    except json.JSONDecodeError:
        messages.error(request, "No se pudo leer el formato enviado.")
        return redirect("editar_rutina", rutina_id)

    semana_str = data.get("semana_id") or request.POST.get("semana_id")
    try:
        semana_id = int(semana_str)
    except (TypeError, ValueError):
        semana_id = getattr(rutina, "semana", 1)

    nuevos = []
    ejercicios_ids = set()

    # Ruta NUEVA (por días)
    if isinstance(data.get("dias"), list):
        for idx_dia, dia in enumerate(data["dias"], start=1):
            # Calentamiento
            for fila in (dia.get("calentamiento") or []):
                if not isinstance(fila, dict):
                    continue
                ej_id = fila.get("ejercicio_id") or fila.get("ejercicio")
                valores = [ej_id, fila.get("series"), fila.get("reps"), fila.get("kilos"), fila.get("rir"), fila.get("notas")]
                if all((v is None or str(v).strip() == "") for v in valores):
                    continue
                ejercicios_ids.add(ej_id)
                nuevos.append({
                    "dia": idx_dia,
                    "es_calentamiento": True,
                    "categoria": "",
                    "ejercicio_id": ej_id,
                    "series": fila.get("series", "") or "",
                    "repeticiones": fila.get("reps", "") or "",
                    "peso": fila.get("kilos", "") or "",
                    "descanso": fila.get("descanso", "") or "",
                    "rir": fila.get("rir", "") or "",
                    "sensaciones": fila.get("sensaciones", "") or "",
                    "notas": fila.get("notas", "") or "",
                })
            # Principal
            for fila in (dia.get("principal") or []):
                if not isinstance(fila, dict):
                    continue
                ej_id = fila.get("ejercicio_id") or fila.get("ejercicio")
                cat = fila.get("categoria", "") or ""
                valores = [cat, ej_id, fila.get("series"), fila.get("reps"), fila.get("kilos"), fila.get("rir"), fila.get("notas")]
                if all((v is None or str(v).strip() == "") for v in valores):
                    continue
                ejercicios_ids.add(ej_id)
                nuevos.append({
                    "dia": idx_dia,
                    "es_calentamiento": False,
                    "categoria": cat,
                    "ejercicio_id": ej_id,
                    "series": fila.get("series", "") or "",
                    "repeticiones": fila.get("reps", "") or "",
                    "peso": fila.get("kilos", "") or "",
                    "descanso": fila.get("descanso", "") or "",
                    "rir": fila.get("rir", "") or "",
                    "sensaciones": fila.get("sensaciones", "") or "",
                    "notas": fila.get("notas", "") or "",
                })
    else:
        # Compat VIEJO: lista plana en data["filas"]
        filas = data.get("filas", []) or []
        for fila in filas:
            if not isinstance(fila, dict):
                continue
            ej_id = fila.get("ejercicio_id") or fila.get("ejercicio")
            valores = [fila.get("categoria"), ej_id, fila.get("series"), fila.get("reps"), fila.get("kilos"), fila.get("rir"), fila.get("notas")]
            if all((v is None or str(v).strip() == "") for v in valores):
                continue
            ejercicios_ids.add(ej_id)
            nuevos.append({
                "dia": 1,
                "es_calentamiento": bool(fila.get("es_calentamiento")),
                "categoria": fila.get("categoria", "") or "",
                "ejercicio_id": ej_id,
                "series": fila.get("series", "") or "",
                "repeticiones": fila.get("reps", "") or "",
                "peso": fila.get("kilos", "") or "",
                "descanso": fila.get("descanso", "") or "",
                "rir": fila.get("rir", "") or "",
                "sensaciones": fila.get("sensaciones", "") or "",
                "notas": fila.get("notas", "") or "",
            })

    # Resolver ejercicios en bloque
    ejercicios_map = Ejercicio.objects.in_bulk({e for e in ejercicios_ids if e})

    with transaction.atomic():
        nueva = Rutina.objects.create(
            member=rutina.member,
            estructura=rutina.estructura,
            semana=semana_id or 1,
        )

        objs = []
        for f in nuevos:
            ej = ejercicios_map.get(f.get("ejercicio_id"))
            objs.append(DetalleRutina(
                rutina=nueva,
                dia=f.get("dia", 1) or 1,
                categoria=f.get("categoria", ""),
                ejercicio=ej,
                series=f.get("series", ""),
                repeticiones=f.get("repeticiones", ""),
                peso=f.get("peso", ""),
                descanso=f.get("descanso", ""),
                rir=f.get("rir", ""),
                sensaciones=f.get("sensaciones", ""),
                notas=f.get("notas", ""),
                es_calentamiento=f.get("es_calentamiento", False),
            ))
        if objs:
            DetalleRutina.objects.bulk_create(objs)

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
    detalles_prefetch = Prefetch(
        "detalles",
        queryset=DetalleRutina.objects.select_related("ejercicio").only(
            "id",
            "rutina_id",
            "dia",
            "categoria",
            "series",
            "repeticiones",
            "peso",
            "descanso",
            "rir",
            "sensaciones",
            "notas",
            "ejercicio__nombre",
        ),
    )
    rutinas = member.rutinas.order_by("-fecha_creacion").prefetch_related(
        detalles_prefetch,
        "comentario",
    )

    rutina_data = {}
    for rutina in rutinas:
        detalles = [
            {
                "dia": detalle.dia,
                "categoria": detalle.categoria,
                "series": detalle.series,
                "repeticiones": detalle.repeticiones,
                "peso": detalle.peso,
                "descanso": detalle.descanso,
                "rir": detalle.rir,
                "sensaciones": detalle.sensaciones,
                "notas": detalle.notas,
                "ejercicio": detalle.ejercicio.nombre if detalle.ejercicio else "",
            }
            for detalle in rutina.detalles.all()
        ]
        rutina_data[str(rutina.id)] = detalles

    rutina_data = json.dumps(rutina_data)

    return render(request, "gymapp/mis_rutinas.html", {
        "member": member,
        "rutinas": rutinas,
        "rutina_data": rutina_data,
    })


