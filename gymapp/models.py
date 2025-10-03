from django.db import models
from decimal import Decimal

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
    PLAN_CHOICES = [
        ("2", "2 días - $24.000"),
        ("3", "3 días - $27.000"),
        ("all", "Todos - $30.000"),
    ]
    PRECIOS = {
        "2": Decimal("24000"),
        "3": Decimal("27000"),
        "all": Decimal("30000"),
    }

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='pagos')
    mes = models.DateField()                      # guardamos el 1° de cada mes
    pagado = models.BooleanField(default=True)
    anulado = models.BooleanField(default=False)  # para “revertir” sin borrar
    fecha_pago = models.DateField(auto_now_add=True)

    # plan y monto. Opcionales para convivir con el botón rápido.
    plan = models.CharField(max_length=8, choices=PLAN_CHOICES, blank=True, null=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['member', 'mes'], name='unique_payment_mes')
        ]

    def save(self, *args, **kwargs):
        # Normalizar SIEMPRE al día 1 para evitar duplicados y facilitar los filtros mensuales
        if self.mes:
            self.mes = self.mes.replace(day=1)

        # Si hay plan y no hay monto manual, setear automático por plan
        if self.plan and not self.monto:
            self.monto = self.PRECIOS.get(self.plan)
        super().save(*args, **kwargs)

    def __str__(self):
        if self.mes:
            return f"{self.member} - {self.mes.strftime('%m-%Y')}"
        return f"{self.member} - (sin mes)"




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
        ("iniciacion", "Iniciación"),
        
    ]

    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name="rutinas")
    estructura = models.CharField(max_length=50, choices=ESTRUCTURAS)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    # Número de semana asociado a la rutina (1-8).  Esto permite
    # conservar la semana seleccionada en el editor de rutinas y mostrarla
    # posteriormente en el historial de rutinas.  Por defecto se asigna la
    # primera semana.
    semana = models.PositiveSmallIntegerField(default=1)

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
