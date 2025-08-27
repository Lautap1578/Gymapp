from django.db import models

# === Socios ===
class Member(models.Model):
    dni = models.CharField(max_length=10, unique=True)
    nombre_apellido = models.CharField(max_length=100)
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    gmail = models.EmailField(max_length=100, blank=True)
    edad = models.PositiveIntegerField(blank=True, null=True)
    historial_deportivo = models.TextField(blank=True)
    experiencias_gimnasios = models.TextField(blank=True)
    historial_lesivo = models.TextField(blank=True)
    enfermedades = models.TextField(blank=True)
    objetivos = models.TextField(blank=True)
    frecuencia_semana = models.CharField(max_length=50, blank=True)
    fecha_alta = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nombre_apellido


# === Pagos ===
class Payment(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='pagos')
    mes = models.CharField(max_length=20)  # Ejemplo: "07-2024"
    pagado = models.BooleanField(default=True)
    anulado = models.BooleanField(default=False)  # Campo para marcar pagos anulados
    fecha_pago = models.DateField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['member', 'mes'], name='unique_payment_mes')
        ]

    def __str__(self):
        return f"{self.member} - {self.mes}"


# === Rutinas ===
class Ejercicio(models.Model):
    nombre = models.CharField(max_length=200, unique=True)

    def __str__(self):
        return self.nombre


class Rutina(models.Model):
    ESTRUCTURAS = [
        ("hipertrofia", "Hipertrofia"),
        ("fuerza_base", "Fuerza base"),
        ("deportista", "Deportista avanzado"),
        ("acondicionamiento", "Acondicionamiento físico"),
        ("edad_temprana", "Edad temprana"),
        ("original", "Original"),
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="rutinas")
    estructura = models.CharField(max_length=50, choices=ESTRUCTURAS)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rutina {self.get_estructura_display()} - {self.member.nombre_apellido} ({self.fecha_creacion.date()})"


class DetalleRutina(models.Model):
    rutina = models.ForeignKey(Rutina, on_delete=models.CASCADE, related_name="detalles")
    categoria = models.CharField(max_length=100, blank=True)  # Ej: Espalda, Piernas
    ejercicio = models.ForeignKey(Ejercicio, on_delete=models.SET_NULL, null=True, blank=True)
    series = models.CharField(max_length=50, blank=True)
    repeticiones = models.CharField(max_length=50, blank=True)
    peso = models.CharField(max_length=50, blank=True)
    descanso = models.CharField(max_length=50, blank=True)
    rir = models.CharField(max_length=50, blank=True)
    sensaciones = models.TextField(blank=True)
    notas = models.TextField(blank=True)
    es_calentamiento = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.rutina} - {self.ejercicio}"


class ComentarioRutina(models.Model):
    rutina = models.OneToOneField(Rutina, on_delete=models.CASCADE, related_name="comentario")
    texto = models.TextField(blank=True)

    def __str__(self):
        return f"Comentario de {self.rutina}"


