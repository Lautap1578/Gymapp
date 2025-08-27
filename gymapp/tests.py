from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from .models import Member, Rutina, DetalleRutina, Ejercicio


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


class MisRutinasQueryTest(TestCase):
    def test_select_related_reduces_queries(self):
        member = Member.objects.create(dni="1", nombre_apellido="Test")
        ejercicio = Ejercicio.objects.create(nombre="Push Up")
        rutina = Rutina.objects.create(member=member, estructura="hipertrofia")

        for _ in range(5):
            DetalleRutina.objects.create(
                rutina=rutina,
                categoria="Fuerza",
                ejercicio=ejercicio,
                series="3",
                repeticiones="10",
            )

        def fetch_with_all():
            return [d.ejercicio.nombre for d in rutina.detalles.all()]

        def fetch_with_select_related():
            return [d.ejercicio.nombre for d in rutina.detalles.select_related("ejercicio")]

        with CaptureQueriesContext(connection) as ctx:
            fetch_with_all()
        queries_all = len(ctx.captured_queries)

        with CaptureQueriesContext(connection) as ctx:
            fetch_with_select_related()
        queries_select = len(ctx.captured_queries)

        self.assertTrue(queries_select < queries_all)

