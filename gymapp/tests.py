from datetime import date

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Member,
    Rutina,
    DetalleRutina,
    Ejercicio,
    Payment,
    ComentarioRutina,
)


class RutinaClienteDuplicationTest(TestCase):
    def test_duplica_calentamiento(self):
        """La duplicación de rutinas preserva los ejercicios de calentamiento"""

        member = Member.objects.create(dni="1", nombre_apellido="Test")
        ejercicio = Ejercicio.objects.create(nombre="Jumping Jacks")

        rutina = Rutina.objects.create(member=member, estructura="hipertrofia")
        DetalleRutina.objects.create(
            rutina=rutina,
            categoria="Movilidad",
            ejercicio=ejercicio,
            repeticiones="10",
            es_calentamiento=True,
        )
        DetalleRutina.objects.create(
            rutina=rutina,
            categoria="Fuerza",
            ejercicio=ejercicio,
            series="3",
            repeticiones="12",
            es_calentamiento=False,
        )

        self.client.post(reverse("rutina_cliente", args=[member.id]))

        self.assertEqual(member.rutinas.count(), 2)
        nueva = member.rutinas.order_by("-fecha_creacion").first()
        self.assertEqual(nueva.detalles.count(), 2)

        calentamientos = nueva.detalles.filter(es_calentamiento=True)
        self.assertEqual(calentamientos.count(), 1)
        self.assertEqual(calentamientos.first().repeticiones, "10")


    def test_duplica_preserva_semana(self):
        """La duplicación de rutinas mantiene el número de semana"""

        member = Member.objects.create(dni="2", nombre_apellido="Tester")
        Rutina.objects.create(member=member, estructura="hipertrofia", semana=4)

        self.client.post(reverse("rutina_cliente", args=[member.id]))

        self.assertEqual(member.rutinas.count(), 2)
        nueva = member.rutinas.order_by("-fecha_creacion").first()
        self.assertEqual(nueva.semana, 4)


class MemberListViewTest(TestCase):
    def test_member_list_displays_members(self):
        member = Member.objects.create(dni="1", nombre_apellido="Tester")
        response = self.client.get(reverse("member_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, member.nombre_apellido)


class MemberRowsPartialViewTest(TestCase):
    def test_unpaid_payment_shows_debe_badge(self):
        member = Member.objects.create(dni="2", nombre_apellido="Tester 2")
        Payment.objects.create(
            member=member,
            mes=date.today(),
            pagado=False,
        )

        response = self.client.get(reverse("member_rows_partial"))

        self.assertEqual(response.status_code, 200)
        self.assertInHTML(
            '<span class="badge bg-danger">Debe</span>',
            response.content.decode(),
        )


class TogglePaymentViewTest(TestCase):
    def test_toggle_payment_creates_and_toggles(self):
        member = Member.objects.create(dni="1", nombre_apellido="Tester")
        url = reverse("toggle_payment", args=[member.id])
        mes_actual = date.today().replace(day=1)

        response = self.client.post(url)
        self.assertRedirects(response, reverse("member_list"))
        pago = Payment.objects.get(member=member, mes=mes_actual)
        self.assertTrue(pago.pagado)
        self.assertFalse(pago.anulado)

        self.client.post(url)
        pago.refresh_from_db()
        self.assertFalse(pago.pagado)
        self.assertFalse(pago.anulado)

        self.client.post(url)
        pago.refresh_from_db()
        self.assertTrue(pago.pagado)
        self.assertFalse(pago.anulado)

    def test_toggle_payment_invalid_member(self):
        response = self.client.post(reverse("toggle_payment", args=[999]))
        self.assertEqual(response.status_code, 404)


class ResumenMensualViewTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(dni="1", nombre_apellido="Tester")
        self.mes_actual = timezone.localdate().replace(day=1)
        Payment.objects.create(
            member=self.member,
            mes=self.mes_actual,
            plan="2",
            pagado=True,
            anulado=False,
        )

    def test_resumen_mensual_default_month(self):
        response = self.client.get(reverse("resumen_mensual"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["mes"], self.mes_actual)
        self.assertEqual(response.context["total_general"], Payment.PRECIOS["2"])

    def test_resumen_mensual_with_query_param(self):
        response = self.client.get(
            reverse("resumen_mensual"),
            {"mes": self.mes_actual.strftime("%Y-%m")},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.member.nombre_apellido)


class LoginClienteViewTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(dni="123", nombre_apellido="Cliente")

    def test_get_login_page(self):
        response = self.client.get(reverse("login_cliente"))
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        response = self.client.post(reverse("login_cliente"), {"dni": "123"})
        self.assertRedirects(response, reverse("mis_rutinas", args=[self.member.id]))
        self.assertEqual(self.client.session["cliente_id"], self.member.id)

    def test_login_invalid_dni(self):
        response = self.client.post(reverse("login_cliente"), {"dni": "999"})
        self.assertRedirects(response, reverse("login_cliente"))
        self.assertNotIn("cliente_id", self.client.session)


class EditarRutinaViewTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(dni="1", nombre_apellido="Tester")
        self.rutina = Rutina.objects.create(member=self.member, estructura="hipertrofia")
        self.ejercicio = Ejercicio.objects.create(nombre="Sentadilla")

    def test_get_editar_rutina(self):
        response = self.client.get(reverse("editar_rutina", args=[self.rutina.id]))
        self.assertEqual(response.status_code, 200)

    def test_post_editar_rutina_creates_details(self):
        url = reverse("editar_rutina", args=[self.rutina.id])
        data = {
            "total_filas_calentamiento": "1",
            "cal_categoria_0": "Movilidad",
            "cal_ejercicio_0": str(self.ejercicio.id),
            "cal_repeticiones_0": "10",
            "cal_descanso_0": "",
            "cal_notas_0": "",
            "total_filas": "1",
            "categoria_0": "Espalda",
            "ejercicio_0": str(self.ejercicio.id),
            "series_0": "3",
            "repeticiones_0": "12",
            "peso_0": "",
            "descanso_0": "",
            "rir_0": "",
            "sensaciones_0": "",
            "notas_0": "",
            "comentario": "Buen entrenamiento",
        }
        response = self.client.post(url, data)
        self.assertRedirects(response, reverse("rutina_cliente", args=[self.member.id]))
        self.assertEqual(self.rutina.detalles.count(), 2)
        self.assertTrue(
            ComentarioRutina.objects.filter(rutina=self.rutina, texto="Buen entrenamiento").exists()
        )

    def test_editar_rutina_invalid_id(self):
        response = self.client.get(reverse("editar_rutina", args=[999]))
        self.assertEqual(response.status_code, 404)


class PaymentModelTest(TestCase):
    def test_payment_str_and_unique(self):
        member = Member.objects.create(dni="1", nombre_apellido="Tester")
        mes = date(2024, 7, 1)
        Payment.objects.create(member=member, mes=mes)
        pago = Payment.objects.get(member=member, mes=mes)
        self.assertEqual(str(pago), f"{member} - {mes.strftime('%m-%Y')}")
        with self.assertRaises(IntegrityError):
            Payment.objects.create(member=member, mes=mes)


class RutinaModelTest(TestCase):
    def test_rutina_str(self):
        member = Member.objects.create(dni="1", nombre_apellido="Tester")
        rutina = Rutina.objects.create(member=member, estructura="hipertrofia")
        esperado = f"Rutina Hipertrofia - {member.nombre_apellido} ({rutina.fecha_creacion.date()})"
        self.assertEqual(str(rutina), esperado)
        self.assertEqual(rutina.detalles.count(), 0)

