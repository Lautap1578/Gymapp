from datetime import date

from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse

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


class MemberListViewTest(TestCase):
    def test_member_list_displays_members(self):
        member = Member.objects.create(dni="1", nombre_apellido="Tester")
        response = self.client.get(reverse("member_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, member.nombre_apellido)


class TogglePaymentViewTest(TestCase):
    def test_toggle_payment_creates_and_toggles(self):
        member = Member.objects.create(dni="1", nombre_apellido="Tester")
        url = reverse("toggle_payment", args=[member.id])
        mes_actual = date.today().replace(day=1)

        response = self.client.post(url)
        self.assertRedirects(response, reverse("member_list"))
        pago = Payment.objects.get(member=member, mes=mes_actual)
        self.assertTrue(pago.pagado)

        self.client.post(url)
        pago.refresh_from_db()
        self.assertFalse(pago.pagado)

        self.client.post(url)
        pago.refresh_from_db()
        self.assertTrue(pago.pagado)

    def test_toggle_payment_invalid_member(self):
        response = self.client.post(reverse("toggle_payment", args=[999]))
        self.assertEqual(response.status_code, 404)


@override_settings(USE_CDN=True)
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


@override_settings(USE_CDN=True)
class LogoutClienteViewTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(dni="456", nombre_apellido="Cliente 2")

    def test_logout_clears_session(self):
        session = self.client.session
        session["cliente_id"] = self.member.id
        session.save()

        response = self.client.get(reverse("logout_cliente"))

        self.assertRedirects(response, reverse("login_cliente"))
        self.assertNotIn("cliente_id", self.client.session)


@override_settings(USE_CDN=True)
class MisRutinasViewTest(TestCase):
    def setUp(self):
        self.member = Member.objects.create(dni="789", nombre_apellido="Cliente 3")
        self.other_member = Member.objects.create(dni="101", nombre_apellido="Cliente 4")

    def test_redirects_to_login_when_not_authenticated(self):
        response = self.client.get(reverse("mis_rutinas", args=[self.member.id]))
        self.assertRedirects(response, reverse("login_cliente"))

    def test_forbidden_when_accessing_other_member(self):
        session = self.client.session
        session["cliente_id"] = self.other_member.id
        session.save()

        response = self.client.get(reverse("mis_rutinas", args=[self.member.id]))
        self.assertEqual(response.status_code, 403)

    def test_allows_access_for_matching_member(self):
        session = self.client.session
        session["cliente_id"] = self.member.id
        session.save()

        response = self.client.get(reverse("mis_rutinas", args=[self.member.id]))
        self.assertEqual(response.status_code, 200)


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

        nueva_rutina = self.member.rutinas.order_by("-fecha_creacion").first()
        self.assertNotEqual(nueva_rutina, self.rutina)
        self.assertEqual(nueva_rutina.detalles.count(), 2)
        self.assertTrue(
            ComentarioRutina.objects.filter(rutina=nueva_rutina, texto="Buen entrenamiento").exists()
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

