from django.urls import path
from . import views

urlpatterns = [
    # Socios
    path('', views.member_list, name='member_list'),
    path('agregar/', views.add_member, name='add_member'),
    path('editar/<int:pk>/', views.edit_member, name='edit_member'),
    path('eliminar/<int:pk>/', views.delete_member, name='delete_member'),

    # Pagos
    path('pagar/<int:member_id>/', views.toggle_payment, name='toggle_payment'),  # POST
    path('historial/<int:member_id>/', views.historial_pagos, name='historial_pagos'),
    path('toggle_pago/<int:member_id>/<str:mes>/', views.toggle_payment_mes, name='toggle_payment_mes'),  # POST
    path('exportar_excel/', views.export_members_excel, name='export_members_excel'),
    path('eliminar_pago/<int:pago_id>/', views.eliminar_pago, name='eliminar_pago'),


    # Cliente login
    path('login_cliente/', views.login_cliente, name='login_cliente'),

    # Partial para recarga con AJAX
    path('member_rows_partial/', views.member_rows_partial, name='member_rows_partial'),
    path('update_member_info/<int:member_id>/', views.update_member_info, name='update_member_info'),

    # Rutinas
    path('rutina/<int:member_id>/', views.rutina_cliente, name='rutina_cliente'),
    path('rutina/editar/<int:rutina_id>/', views.editar_rutina, name='editar_rutina'),
    path('rutina/eliminar/<int:rutina_id>/', views.eliminar_rutina, name='eliminar_rutina'),
    path('socio/<int:member_id>/rutina/nueva/<str:tipo>/', views.crear_rutina, name='crear_rutina'),
    path('rutina/guardar/<int:rutina_id>/', views.guardar_rutina, name='guardar_rutina'),

    # Rutinas cliente
    path('mis_rutinas/<int:member_id>/', views.mis_rutinas, name='mis_rutinas'),
]

