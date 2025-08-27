from datetime import date, datetime
import json
import openpyxl
from django.db.models import Q, F
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from django.db import transaction

from .forms import MemberForm, MemberInfoForm, DetalleRutinaFormSet
from .models import Member, Payment, Ejercicio, Rutina, DetalleRutina, ComentarioRutina

from django.utils import timezone
from django.views.decorators.http import require_POST



# === Socios ===

def member_list(request):
    q = request.GET.get("q") or ""
    members = Member.objects.filter(
        Q(nombre_apellido__icontains=q) |
        Q(gmail__icontains=q) |
        Q(telefono__icontains=q) |
        Q(dni__icontains=q)
    ).order_by("nombre_apellido")

    current_month = date.today().replace(day=1)
    pagos_ids = set(
        p.member_id for p in Payment.objects.filter(anulado=False, mes=current_month)
    )

    return render(request, "gymapp/member_list.html", {
        "members": members,
        "pagos_ids": pagos_ids,
        "current_month": current_month,
    })


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


# === Pagos ===

@require_POST
def toggle_payment(request, member_id):
    member = get_object_or_404(Member, pk=member_id)
    mes_actual = date.today().replace(day=1)

    pago = Payment.objects.filter(member=member, mes=mes_actual).first()
    if pago:
        pago.anulado = not pago.anulado
        pago.save()
    else:
        Payment.objects.create(member=member, mes=mes_actual)
    return redirect('member_list')


def historial_pagos(request, member_id):
    from datetime import date as _date
    member = get_object_or_404(Member, pk=member_id)
    pagos = Payment.objects.filter(member=member, anulado=False)

    historial = []
    hoy = _date.today().replace(day=1)
    fecha = member.fecha_alta.replace(day=1)

    while fecha <= hoy:
        mes_str = fecha.strftime("%m-%Y")
        pagado = pagos.filter(mes=fecha).exists()
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
def toggle_payment_mes(request, member_id, mes):
    member = get_object_or_404(Member, pk=member_id)
    mes_date = datetime.strptime(mes, "%m-%Y").date().replace(day=1)
    pago = Payment.objects.filter(member=member, mes=mes_date).first()
    if pago:
        pago.anulado = not pago.anulado
        pago.save()
    else:
        Payment.objects.create(member=member, mes=mes_date, pagado=True)
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
        p.member_id for p in Payment.objects.filter(anulado=False, mes=current_month)
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
    """Lista rutinas de un socio y opción para crear nueva"""
    member = get_object_or_404(Member, pk=member_id)
    rutinas = member.rutinas.order_by("-fecha_creacion")

    if request.method == "POST":
        # Crear nueva rutina duplicando la última existente
        ultima = rutinas.first()
        if ultima:
            nueva = Rutina.objects.create(member=member, estructura=ultima.estructura)
            # duplicar detalles en bloque
            detalles = ultima.detalles.select_related("ejercicio").values(
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
                ComentarioRutina.objects.create(rutina=nueva, texto=ultima.comentario.texto)
        else:
            # si no hay rutinas, crear vacía por defecto
            estructura = request.POST.get("estructura", "hipertrofia")
            nueva = Rutina.objects.create(member=member, estructura=estructura)

        return redirect("editar_rutina", nueva.id)

    return render(request, "gymapp/rutina_cliente.html", {
        "member": member,
        "rutinas": rutinas
    })


def crear_rutina(request, member_id, tipo):
    """Crea una rutina nueva desde un tipo elegido"""
    member = get_object_or_404(Member, id=member_id)

    # mapeo de nombres legibles → clave de choices
    mapping = {
        "Hipertrofia": "hipertrofia",
        "Acondicionamiento físico": "acondicionamiento",
        "Deportista avanzado": "deportista",
        "Edad temprana": "edad_temprana",
        "Fuerza base": "fuerza_base",
        "Original": "original",
    }

    clave = mapping.get(tipo, "hipertrofia")

    Rutina.objects.create(
        member=member,
        estructura=clave,
    )

    return redirect("rutina_cliente", member_id=member.id)


def editar_rutina(request, rutina_id):
    rutina = get_object_or_404(Rutina, pk=rutina_id)

    # Ejercicios para los selects (se guarda ejercicio_id)
    ejercicios = Ejercicio.objects.all().order_by("nombre")


    categorias = [
    "Pectorales", "Espalda", "Deltoides", "Bíceps", "Tríceps",
    "Cuádriceps", "Isquiotibiales", "Pantorrilla", "Abdomen",
    "Trapecios", "Antebrazos"
]

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
                rutina.detalles.all().delete()

                nuevos_detalles = [
                    DetalleRutina(rutina=rutina, **form.cleaned_data)
                    for form in formset.forms
                    if form.cleaned_data
                ]
                DetalleRutina.objects.bulk_create(nuevos_detalles)

                texto = request.POST.get("comentario", "")
                if hasattr(rutina, "comentario"):
                    rutina.comentario.texto = texto
                    rutina.comentario.save()
                else:
                    ComentarioRutina.objects.create(rutina=rutina, texto=texto)

            return redirect("rutina_cliente", rutina.member.id)

    return render(request, "gymapp/editar_rutina.html", {
        "rutina": rutina,
        "ejercicios": ejercicios,
        "categorias": categorias,
        "detalles": rutina.detalles.filter(es_calentamiento=False),
        "calentamiento": rutina.detalles.filter(es_calentamiento=True),
        "comentario": getattr(rutina, "comentario", None)
    })




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
                "categoria",
                "series",
                "repeticiones",
                "peso",
                "descanso",
                "rir",
                "sensaciones",
                "notas",
                ejercicio=F("ejercicio__nombre"),
            )
        )
        rutina_data[str(rutina.id)] = data

    rutina_data = json.dumps(rutina_data)

    return render(request, "gymapp/mis_rutinas.html", {
        "member": member,
        "rutinas": rutinas,
        "rutina_data": rutina_data,
    })
