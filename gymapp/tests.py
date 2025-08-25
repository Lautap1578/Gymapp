from django.test import TestCase
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

