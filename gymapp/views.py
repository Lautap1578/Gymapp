from __future__ import annotations

import json
from datetime import date, datetime

import openpyxl
from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .constants import RUTINA_SLUGS  # fuente única de slugs/títulos (read-only)
from .forms import (
    DetalleRutinaFormSet,
    DetalleRutinaPayloadForm,  # (no se usa acá pero se mantiene el import público)
    MemberForm,
    MemberInfoForm,
)
from .models import ComentarioRutina, DetalleRutina, Ejercicio, Member, Payment, Rutina


# =========================
#        SOCIOS
# =========================

def member_list(request):
    q = (request.GET.get("q") or "").strip()

    members = Member.objects.all().order_by("nombre_apellido")
    if q:
        members = members.filter(
            Q(nombre_apellido__icontains=q)
            | Q(dni__icontains=q)
            | Q(telefono__icontains=q)
            | Q(gmail__icontains=q)
        )

    today = date.today()
    current_month = today.replace(day=1)

    pagos_ids = set(
        Payment.objects.filter(mes=current_month, pagado=True, anulado=False).values_list(
            "member_id", flat=True
        )
    )
    context = {
        "members": members,
        "current_month": current_month,
    }
    return render(request, "gymapp/member_list.html", context)


def add_member(request):
    if request.method == "POST":
        form = MemberForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("member_list")
    else:
        form = MemberForm()
    return render(request, "gymapp/add_member.html", {"form": form})


def edit_member(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        form = MemberForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
            return redirect("member_list")
    else:
        form = MemberForm(instance=member)
    return render(request, "gymapp/edit_member.html", {"form": form})


def delete_member(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == "POST":
        member.delete()
        return redirect("member_list")
    return render(request, "gymapp/confirm_delete.html", {"member": member})


# =========================
#         PAGOS
# =========================

@require_POST
def toggle_payment(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    mes_actual = date.today().replace(day=1)
    pago, created = Payment.objects.get_or_create(
        member=member, mes=mes_actual, defaults={"pagado": True}
    )
    if not created:
        pago.pagado = not pago.pagado
        pago.save(update_fields=["pagado"])
    return redirect("member_list")


def historial_pagos(request, member_id):
    member = get_object_or_404(Member, pk=member_id)

    pagos_realizados = Payment.objects.filter(
        member=member, pagado=True, anulado=False
    ).values_list("mes", flat=True)
    meses_pagados = {mes.replace(day=1) for mes in pagos_realizados if mes is not None}

    historial = []
    hoy = date.today().replace(day=1)
    fecha = member.fecha_alta.replace(day=1)

    while fecha <= hoy:
        mes_str = fecha.strftime("%m-%Y")
        pagado = fecha in meses_pagados
        historial.append({"mes": mes_str, "pagado": pagado})
        # avanzar 1 mes
        if fecha.month == 12:
            fecha = fecha.replace(year=fecha.year + 1, month=1)
        else:
            fecha = fecha.replace(month=fecha.month + 1)

    return render(
        request,
        "gymapp/historial_pagos.html",
        {"member": member, "historial": historial},
    )


@require_POST
def eliminar_pago(request, pago_id):
    pago = get_object_or_404(Payment, id=pago_id)
    pago.anulado = True
    pago.save(update_fields=["anulado"])
    return redirect("historial_pagos", member_id=pago.member_id)


@require_POST
def toggle_payment_mes(request, member_id, mes):
    member = get_object_or_404(Member, pk=member_id)
    try:
        mes_date = datetime.strptime(mes, "%m-%Y").date().replace(day=1)
    except Exception:
        mes_date = date.today().replace(day=1)

    pago, created = Payment.objects.get_or_create(
        member=member, mes=mes_date, defaults={"pagado": True}
    )
    if not created:
        pago.pagado = not pago.pagado
        pago.save(update_fields=["pagado"])
    return redirect("historial_pagos", member_id=member_id)


def export_members_excel(request):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Socios"

    headers = [
        "Nombre y Apellido",
        "DNI",
        "Gmail",
        "Teléfono",
        "Dirección",
        "Edad",
        "Historial Deportivo",
        "Experiencias Gimnasios",
        "Historial Lesivo",
        "Enfermedades",
        "Objetivos",
        "Frecuencia Semana",
    ]
    ws.append(headers)

    for m in Member.objects.all():
        ws.append(
            [
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
                m.frecuencia_semana or "",
            ]
        )

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = 'attachment; filename="socios.xlsx"'
    wb.save(response)
    return response


def login_cliente(request):
    if request.method == "POST":
        dni = (request.POST.get("dni") or "").strip()
        if not dni:
            messages.warning(request, "Ingresá tu DNI.")
            return redirect("login_cliente")
        try:
            member = Member.objects.get(dni=dni)
        except Member.DoesNotExist:
            messages.error(request, "DNI no registrado. Verificá los datos.")
            return redirect("login_cliente")

        request.session["cliente_id"] = member.id
        messages.success(request, f"Bienvenido, {member.nombre_apellido}.")
        return redirect("mis_rutinas", member.id)

    return render(request, "gymapp/login_cliente.html")


def member_rows_partial(request):
    q = request.GET.get("q") or ""
    members = (
        Member.objects.filter(
            Q(nombre_apellido__icontains=q)
            | Q(gmail__icontains=q)
            | Q(telefono__icontains=q)
            | Q(dni__icontains=q)
        )
        .order_by("nombre_apellido")
    )

    current_month = date.today().replace(day=1)
    pagos_ids = {
        p.member_id
        for p in Payment.objects.filter(
            anulado=False, pagado=True, mes=current_month
        ).only("member_id")
    }

    return render(
        request,
        "gymapp/partials/_member_rows.html",
        {"members": members, "pagos_ids": pagos_ids, "current_month": current_month},
    )


def update_member_info(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    if request.method == "POST":
        form = MemberInfoForm(request.POST, instance=member)
        if form.is_valid():
            form.save()
    return redirect("member_list")


# =========================
#         RUTINAS
# =========================

def rutina_cliente(request, member_id):
    member = get_object_or_404(Member, pk=member_id)

    # Prefetch optimizado para detalles + comentario
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

    rutinas = (
        member.rutinas.order_by("-fecha_creacion")
        .prefetch_related(detalles_prefetch, "comentario")
    )

    if request.method == "POST":
        ultima = rutinas.first()
        if ultima:
            with transaction.atomic():
                nueva = Rutina.objects.create(
                    member=member,
                    estructura=ultima.estructura,
                    semana=ultima.semana,
                )
                detalles = ultima.detalles.select_related("ejercicio").values(
                    "dia",
                    "categoria",
                    "ejercicio_id",
                    "series",
                    "repeticiones",
                    "peso",
                    "descanso",
                    "rir",
                    "sensaciones",
                    "notas",
                    "es_calentamiento",
                )
                DetalleRutina.objects.bulk_create(
                    [DetalleRutina(rutina=nueva, **d) for d in detalles]
                )
                if hasattr(ultima, "comentario"):
                    ComentarioRutina.objects.create(
                        rutina=nueva, texto=ultima.comentario.texto
                    )
        else:
            estructura = request.POST.get("estructura", "hipertrofia")
            Rutina.objects.create(member=member, estructura=estructura)

        return redirect("editar_rutina", rutinas.first().id if rutinas else member.rutinas.latest("id").id)

    # Render (GET): listado de rutinas
    return render(
        request,
        "gymapp/rutina_cliente.html",
        {"member": member, "rutinas": rutinas},
    )


def crear_rutina(request, member_id, tipo):
    """
    Crea una rutina con el slug interno correspondiente.
    Respeta los slugs definidos por constants.py (RUTINA_SLUGS) y tus subtipos de hipertrofia.
    """
    import unicodedata

    member = get_object_or_404(Member, id=member_id)

    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
        return (s or "").lower().strip()

    label = _norm(tipo)

    # Slugs principales según constants (read-only)
    # NOTA: no usamos RUTINA_SLUGS keys directamente porque también aceptamos labels “bonitos”.
    mapping = {
        "hipertrofia": "hipertrofia",
        "acondicionamiento fisico": "acondicionamiento",
        "acondicionamiento": "acondicionamiento",
        "deportista avanzado": "deportista",
        "edad temprana": "edad_temprana",
        "fuerza base": "fuerza_base",
        # subtipos hipertrofia (se conservan tal cual los usás en templates/JS)
        "hip_fullbody": "hip_fullbody",
        "hip_torso_pierna_h": "hip_torso_pierna_h",
        "hip_torso_pierna_m": "hip_torso_pierna_m",
        "hip_empuje_tracciones_h": "hip_empuje_tracciones_h",
        "hip_empuje_tracciones_m": "hip_empuje_tracciones_m",
        "hip_weider_h": "hip_weider_h",
        "hip_weider_m": "hip_weider_m",
    }

    clave = mapping.get(label, "fuerza_base")
    Rutina.objects.create(member=member, estructura=clave)
    return redirect("rutina_cliente", member_id=member.id)


def editar_rutina(request, rutina_id):
    """
    Editor de rutinas. Para fuerza_base soporta múltiples DÍAS (día = parte inicial + parte principal).
    Mantiene compatibilidad con el flujo viejo (formset) y otras estructuras.
    """
    rutina = get_object_or_404(Rutina, pk=rutina_id)
    ejercicios = Ejercicio.objects.all().order_by("nombre")

    # ========== Flujo viejo (formset) ==========
    if request.method == "POST" and "detalles-TOTAL_FORMS" in request.POST:
        detalles_data = []

        # Calentamiento
        filas_c = int(request.POST.get("total_filas_calentamiento", 0) or 0)
        for i in range(filas_c):
            detalles_data.append(
                {
                    "categoria": request.POST.get(f"cal_categoria_{i}", ""),
                    "ejercicio": request.POST.get(f"cal_ejercicio_{i}") or None,
                    "repeticiones": request.POST.get(f"cal_repeticiones_{i}", ""),
                    "descanso": request.POST.get(f"cal_descanso_{i}", ""),
                    "notas": request.POST.get(f"cal_notas_{i}", ""),
                    "es_calentamiento": True,
                }
            )

        # Principal
        filas = int(request.POST.get("total_filas", 0) or 0)
        for i in range(filas):
            detalles_data.append(
                {
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
                }
            )

        # Construimos el formset “viejo” sobre una NUEVA Rutina (versionado)
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
                        nuevos.append(
                            DetalleRutina(rutina=nueva, dia=1, **data)  # día=1 en flujo viejo
                        )
                if nuevos:
                    DetalleRutina.objects.bulk_create(nuevos)

                texto = request.POST.get("comentario", "")
                if not texto and hasattr(rutina, "comentario"):
                    texto = rutina.comentario.texto
                if texto:
                    ComentarioRutina.objects.create(rutina=nueva, texto=texto)

                messages.success(request, "Se creó una nueva versión de la rutina.")
            return redirect("rutina_cliente", rutina.member.id)

        messages.error(request, "Revisá los datos: hay campos inválidos o incompletos.")

    # ========== GET: armar contexto ==========
    # Estructura por defecto para fuerza_base (categorías sugeridas)
    categorias_fb = ["Cadena anterior", "Tracciones", "Cadena posterior", "Empujes"]

    # --- Fuerza base ---
    if rutina.estructura == "fuerza_base":
        detalles = rutina.detalles.select_related("ejercicio").order_by("dia", "id")

        # Mapear por día
        dias_map: dict[int, dict[str, list[dict]]] = {}
        for d in detalles:
            dia = d.dia or 1
            dias_map.setdefault(dia, {"calentamiento": [], "principal": []})

            base = {
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "ejercicio_txt": d.ejercicio.nombre if d.ejercicio else "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                "rir": d.rir or "",
                "notas": d.notas or "",
            }
            if d.es_calentamiento:
                dias_map[dia]["calentamiento"].append(base)
            else:
                fila_p = dict(base)
                fila_p["categoria"] = d.categoria or ""
                dias_map[dia]["principal"].append(fila_p)

        # Si no había datos, crear un día 1 base con 4 categorías
        if not dias_map:
            dias_map[1] = {
                "calentamiento": [],
                "principal": [
                    {
                        "categoria": c,
                        "ejercicio_id": "",
                        "series": "",
                        "reps": "",
                        "kilos": "",
                        "rir": "",
                        "notas": "",
                    }
                    for c in categorias_fb
                ],
            }

        # Normalizar estructura de render
        dias = []
        for dia_idx in sorted(dias_map.keys()):
            cal = dias_map[dia_idx]["calentamiento"]
            pr = dias_map[dia_idx]["principal"]
            if not pr:
                pr = [
                    {
                        "categoria": c,
                        "ejercicio_id": "",
                        "series": "",
                        "reps": "",
                        "kilos": "",
                        "rir": "",
                        "notas": "",
                    }
                    for c in categorias_fb
                ]
            dias.append({"numero": dia_idx, "calentamiento": cal, "principal": pr})

        semanas = [{"id": i, "numero": i} for i in range(1, 9)]
        semana_activa_id = getattr(rutina, "semana", 1) or 1

        contexto = {
            "rutina": rutina,
            "ejercicios": ejercicios,
            "categorias": categorias_fb,
            "dias": dias,
            "semanas": semanas,
            "semana_activa_id": semana_activa_id,
            "vista_por_semanas": False,
        }
        return render(request, "gymapp/editar_rutina_fuerza_base.html", contexto)

    # --- Acondicionamiento ---
    if rutina.estructura == "acondicionamiento":
        filas_cal = []
        for d in rutina.detalles.filter(es_calentamiento=True).select_related("ejercicio"):
            filas_cal.append(
                {
                    "id": d.id,
                    "ejercicio_id": d.ejercicio_id or "",
                    "ejercicio_txt": d.ejercicio.nombre if d.ejercicio else "",
                    "series": d.series or "",
                    "reps": d.repeticiones or "",
                    "kilos": d.peso or "",
                    "notas": d.notas or "",
                }
            )
        if not filas_cal:
            filas_cal = [
                {"id": None, "ejercicio_id": "", "ejercicio_txt": "", "series": "", "reps": "", "kilos": "", "notas": ""}
                for _ in range(3)
            ]

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
                filas_principal.append(
                    {
                        "id": det.id,
                        "categoria": cat,
                        "ejercicio_id": det.ejercicio_id or "",
                        "ejercicio_txt": det.ejercicio.nombre if det.ejercicio else "",
                        "series": det.series or "",
                        "reps": det.repeticiones or "",
                        "kilos": det.peso or "",
                        "notas": det.notas or "",
                    }
                )
            else:
                filas_principal.append(
                    {
                        "id": None,
                        "categoria": cat,
                        "ejercicio_id": "",
                        "ejercicio_txt": "",
                        "series": "",
                        "reps": "",
                        "kilos": "",
                        "notas": "",
                    }
                )

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

    # --- Edad temprana ---
    if rutina.estructura == "edad_temprana":
        filas_inicial = []
        for d in rutina.detalles.filter(es_calentamiento=True).select_related("ejercicio"):
            filas_inicial.append(
                {
                    "id": d.id,
                    "ejercicio_id": d.ejercicio_id or "",
                    "ejercicio_txt": d.ejercicio.nombre if d.ejercicio else "",
                    "series": d.series or "",
                    "reps": d.repeticiones or "",
                    "kilos": d.peso or "",
                    "notas": d.notas or "",
                }
            )
        if not filas_inicial:
            filas_inicial = [
                {"id": None, "ejercicio_id": "", "ejercicio_txt": "", "series": "", "reps": "", "kilos": "", "notas": ""}
                for _ in range(4)
            ]

        filas_principal = []
        for d in rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"):
            filas_principal.append(
                {
                    "id": d.id,
                    "categoria": d.categoria or "",
                    "ejercicio_id": d.ejercicio_id or "",
                    "ejercicio_txt": d.ejercicio.nombre if d.ejercicio else "",
                    "series": d.series or "",
                    "reps": d.repeticiones or "",
                    "kilos": d.peso or "",
                    "notas": d.notas or "",
                }
            )
        if not filas_principal:
            filas_principal = [
                {"id": None, "categoria": "", "ejercicio_id": "", "ejercicio_txt": "", "series": "", "reps": "", "kilos": "", "notas": ""}
                for _ in range(2)
            ]

        semanas = [{"id": i, "numero": i} for i in range(1, 9)]
        semana_activa_id = getattr(rutina, "semana", 1) or 1

        contexto = {
            "rutina": rutina,
            "ejercicios": ejercicios,
            "filas_inicial": filas_inicial,
            "filas_principal": filas_principal,
            "semanas": semanas,
            "semana_activa_id": semana_activa_id,
            "titulo_rutina": "Edad temprana",
        }
        return render(request, "gymapp/editar_rutina_edad_temprana.html", contexto)

    # --- Deportista avanzado ---
    if rutina.estructura == "deportista":
        # Parte inicial (calentamiento)
        filas_inicial = []
        for d in rutina.detalles.filter(categoria="inicial").select_related("ejercicio"):
            filas_inicial.append(
                {
                    "id": d.id,
                    "ejercicio_id": d.ejercicio_id or "",
                    "ejercicio_txt": d.ejercicio.nombre if d.ejercicio else "",
                    "series": d.series or "",
                    "reps": d.repeticiones or "",
                    "kilos": d.peso or "",
                    "notas": d.notas or "",
                }
            )
        if not filas_inicial:
            filas_inicial = [
                {"id": None, "ejercicio_id": "", "ejercicio_txt": "", "series": "", "reps": "", "kilos": "", "notas": ""}
                for _ in range(3)
            ]

        # Parte fuerza (categorías fijas)
        categorias_fuerza = ["Cadena anterior", "Cadena posterior", "Empujes/Tracciones"]
        filas_fuerza = []
        detalles_fuerza = {d.categoria: d for d in rutina.detalles.filter(categoria__in=categorias_fuerza).select_related("ejercicio")}
        
        for cat in categorias_fuerza:
            det = detalles_fuerza.get(cat)
            if det:
                filas_fuerza.append({
                    "categoria": cat,
                    "ejercicio_id": det.ejercicio_id or "",
                    "ejercicio_txt": det.ejercicio.nombre if det.ejercicio else "",
                    "series": det.series or "",
                    "reps": det.repeticiones or "",
                    "kilos": det.peso or "",
                    "rir": det.rir or "",
                    "notas": det.notas or "",
                })
            else:
                filas_fuerza.append({
                    "categoria": cat,
                    "ejercicio_id": "",
                    "ejercicio_txt": "",
                    "series": "",
                    "reps": "",
                    "kilos": "",
                    "rir": "",
                    "notas": "",
                })

        # Parte potencia
        filas_potencia = []
        for d in rutina.detalles.filter(categoria="potencia").select_related("ejercicio"):
            filas_potencia.append(
                {
                    "id": d.id,
                    "ejercicio_id": d.ejercicio_id or "",
                    "ejercicio_txt": d.ejercicio.nombre if d.ejercicio else "",
                    "series": d.series or "",
                    "reps": d.repeticiones or "",
                    "kilos": d.peso or "",
                    "notas": d.notas or "",
                }
            )
        if not filas_potencia:
            filas_potencia = [
                {"id": None, "ejercicio_id": "", "ejercicio_txt": "", "series": "", "reps": "", "kilos": "", "notas": ""}
                for _ in range(3)
            ]

        # Parte accesorios
        filas_accesorios = []
        for d in rutina.detalles.filter(categoria="accesorios").select_related("ejercicio"):
            filas_accesorios.append(
                {
                    "id": d.id,
                    "ejercicio_id": d.ejercicio_id or "",
                    "ejercicio_txt": d.ejercicio.nombre if d.ejercicio else "",
                    "series": d.series or "",
                    "reps": d.repeticiones or "",
                    "kilos": d.peso or "",
                    "notas": d.notas or "",
                }
            )
        if not filas_accesorios:
            filas_accesorios = [
                {"id": None, "ejercicio_id": "", "ejercicio_txt": "", "series": "", "reps": "", "kilos": "", "notas": ""}
                for _ in range(3)
            ]

        semanas = [{"id": i, "numero": i} for i in range(1, 9)]
        semana_activa_id = getattr(rutina, "semana", 1) or 1

        contexto = {
            "rutina": rutina,
            "ejercicios": ejercicios,  # mismo queryset ordenado
            "filas_inicial": filas_inicial,
            "filas_fuerza": filas_fuerza,
            "filas_potencia": filas_potencia,
            "filas_accesorios": filas_accesorios,
            "semanas": semanas,
            "semana_activa_id": semana_activa_id,
        }
        return render(request, "gymapp/editar_rutina_deportista_avanzado.html", contexto)

    # --- Fallback genérico ---
    filas_ctx = []
    for d in rutina.detalles.filter(es_calentamiento=False).select_related("ejercicio"):
        filas_ctx.append(
            {
                "id": d.id,
                "ejercicio_id": d.ejercicio_id or "",
                "series": d.series or "",
                "reps": d.repeticiones or "",
                "kilos": d.peso or "",
                "rir": d.rir or "",
                "notas": d.notas or "",
            }
        )

    semanas = [{"id": i, "numero": i} for i in range(1, 9)]
    semana_activa_id = getattr(rutina, "semana", 1) or 1

    contexto = {
        "rutina": rutina,
        "ejercicios": ejercicios,
        "detalles": rutina.detalles.filter(es_calentamiento=False),
        "calentamiento": rutina.detalles.filter(es_calentamiento=True),
        "comentario": getattr(rutina, "comentario", None),
        "filas": filas_ctx,
        "semanas": semanas,
        "semana_activa_id": semana_activa_id,
        "vista_por_semanas": False,
        "categorias": [
            "Pectorales",
            "Espalda",
            "Deltoides",
            "Bíceps",
            "Tríceps",
            "Cuádriceps",
            "Isquiotibiales",
            "Pantorrilla",
            "Abdomen",
            "Trapecios",
            "Antebrazos",
        ],
    }
    return render(request, "gymapp/editar_rutina.html", contexto)


def hipertrofia_opciones(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    subtipos = [
        ("hip_fullbody", "Fullbody"),
        ("hip_torso_pierna_h", "Torso-Pierna Hombre"),
        ("hip_torso_pierna_m", "Torso-Pierna Mujer"),
        ("hip_empuje_tracciones_h", "Empuje-Tracciones Hombre"),
        ("hip_empuje_tracciones_m", "Empuje-Tracciones Mujer"),
        ("hip_weider_h", "Weider Hombre"),
        ("hip_weider_m", "Weider Mujer"),
    ]
    return render(
        request,
        "gymapp/hipertrofia_opciones.html",
        {"member": member, "subtipos": subtipos},
    )


@require_POST
def guardar_rutina(request, rutina_id):
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
        messages.error(request, "Semana inválida.")
        return redirect("editar_rutina", rutina_id)
        
    nuevos = []
    ejercicios_txt = set()  # nombres escritos
    ejercicios_ids = set()  # ids referenciados

    def _resolver_ej_id(fila: dict) -> int | None:
        ej_id = fila.get("ejercicio_id") or fila.get("ejercicio")
        nombre = (fila.get("ejercicio_txt") or "").strip()
        if ej_id:
            try:
                return int(ej_id)
            except (TypeError, ValueError):
                pass
        if nombre:
            ejercicios_txt.add(nombre)
        return None

    # Ruta NUEVA (por días)
    if isinstance(data.get("dias"), list):
        for idx_dia, dia in enumerate(data["dias"], start=1):
            # Calentamiento
            for fila in (dia.get("calentamiento") or []):
                if not isinstance(fila, dict):
                    continue
                ej_id = _resolver_ej_id(fila)
                valores = [
                    fila.get("series"),
                    fila.get("reps"),
                    fila.get("kilos"),
                    fila.get("rir"),
                    fila.get("notas"),
                    fila.get("ejercicio_txt"),
                ]
                if all((v is None or str(v).strip() == "") for v in valores):
                    continue
                if ej_id:
                    ejercicios_ids.add(ej_id)
                nuevos.append(
                    {
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
                        "ejercicio_txt": (fila.get("ejercicio_txt") or "").strip(),
                    }
                )
            # Principal
            for fila in (dia.get("principal") or []):
                if not isinstance(fila, dict):
                    continue
                ej_id = _resolver_ej_id(fila)
                cat = fila.get("categoria", "") or ""
                valores = [
                    cat,
                    fila.get("series"),
                    fila.get("reps"),
                    fila.get("kilos"),
                    fila.get("rir"),
                    fila.get("notas"),
                    fila.get("ejercicio_txt"),
                ]
                if all((v is None or str(v).strip() == "") for v in valores):
                    continue
                if ej_id:
                    ejercicios_ids.add(ej_id)
                nuevos.append(
                    {
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
                        "ejercicio_txt": (fila.get("ejercicio_txt") or "").strip(),
                    }
                )
    else:
        # Compat VIEJO
        filas = data.get("filas", []) or []
        for fila in filas:
            if not isinstance(fila, dict):
                continue
            ej_id = _resolver_ej_id(fila)
            valores = [
                fila.get("categoria"),
                fila.get("series"),
                fila.get("reps"),
                fila.get("kilos"),
                fila.get("rir"),
                fila.get("notas"),
                fila.get("ejercicio_txt"),
            ]
            if all((v is None or str(v).strip() == "") for v in valores):
                continue
            if ej_id:
                ejercicios_ids.add(ej_id)
            nuevos.append(
                {
                    "dia": fila.get("dia", 1) or 1,
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
                    "ejercicio_txt": (fila.get("ejercicio_txt") or "").strip(),
                }
            )

    # 1) Resolver por ids existentes
    ejercicios_map = Ejercicio.objects.in_bulk({e for e in ejercicios_ids if e})

    # 2) Resolver por nombres escritos (crear si no existen)
    existentes_por_nombre = {}
    if ejercicios_txt:
        existentes = Ejercicio.objects.filter(nombre__in=list(ejercicios_txt))
        existentes_por_nombre = {e.nombre.lower(): e for e in existentes}
        for nombre in ejercicios_txt:
            key = nombre.lower()
            if key not in existentes_por_nombre:
                e = Ejercicio.objects.create(nombre=nombre)
                existentes_por_nombre[key] = e

    with transaction.atomic():
        nueva = Rutina.objects.create(
            member=rutina.member,
            estructura=rutina.estructura,
            semana=semana_id or 1,
        )

        objs = []
        for f in nuevos:
            ej = None
            if f.get("ejercicio_id"):
                ej = ejercicios_map.get(f["ejercicio_id"])
            if not ej:
                nombre = (f.get("ejercicio_txt") or "").strip()
                if nombre:
                    ej = existentes_por_nombre.get(nombre.lower())
                    if not ej:
                        ej = Ejercicio.objects.filter(nombre__iexact=nombre).first()
                        if not ej:
                            ej = Ejercicio.objects.create(nombre=nombre)

            objs.append(
                DetalleRutina(
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
                )
            )

        if objs:
            DetalleRutina.objects.bulk_create(objs)

        if hasattr(rutina, "comentario") and rutina.comentario and rutina.comentario.texto:
            ComentarioRutina.objects.create(rutina=nueva, texto=rutina.comentario.texto)

    messages.success(request, "Se creó una nueva versión de la rutina.")
    return redirect("rutina_cliente", rutina.member.id)


def eliminar_rutina(request, rutina_id):
    rutina = get_object_or_404(Rutina, id=rutina_id)
    member_id = rutina.member.id
    nombre = (
        rutina.get_estructura_display()
        if hasattr(rutina, "get_estructura_display")
        else rutina.estructura
    )
    rutina.delete()
    return redirect("rutina_cliente", member_id=member_id)


def mis_rutinas(request, member_id):
    member = get_object_or_404(Member, pk=member_id)

    ultima_rutina = (
        member.rutinas.order_by("-fecha_creacion")
        .prefetch_related("detalles__ejercicio", "comentario")
        .first()
    )

    if not ultima_rutina:
        return render(
            request,
            "gymapp/mis_rutinas.html",
            {
                "member": member,
                "ultima_rutina": None,
                "rutina_data": json.dumps({}),
                "USE_CDN": True,
            },
        )

    detalles = [
        {
            "dia": d.dia,
            "categoria": d.categoria,
            "series": d.series,
            "repeticiones": d.repeticiones,
            "peso": d.peso,
            "descanso": d.descanso,
            "rir": d.rir,
            "sensaciones": d.sensaciones,
            "notas": d.notas,
            "ejercicio": d.ejercicio.nombre if d.ejercicio else "",
        }
        for d in ultima_rutina.detalles.all()
    ]

    rutina_data = json.dumps({str(ultima_rutina.id): detalles})

    return render(
        request,
        "gymapp/mis_rutinas.html",
        {
            "member": member,
            "ultima_rutina": ultima_rutina,
            "rutina_data": rutina_data,
            "USE_CDN": True,
        },
    )

