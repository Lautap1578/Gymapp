from django.contrib import admin
from .models import Member, Payment

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ("nombre_apellido", "dni", "gmail", "telefono", "fecha_alta")
    search_fields = ("nombre_apellido", "dni", "gmail", "telefono")
    list_filter = ("fecha_alta",)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("member", "mes", "plan", "monto", "pagado", "anulado", "fecha_pago")
    list_filter = ("mes", "plan", "anulado")
    search_fields = ("member__nombre_apellido", "member__dni")
