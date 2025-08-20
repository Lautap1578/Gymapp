# gym

Proyecto Django para gestión de socios y pagos de gimnasio.

## Instalación

1. Crear y activar un entorno virtual:
    ```
    python -m venv env
    env\Scripts\activate  # Windows
    # source env/bin/activate  # Linux/Mac
    ```
2. Instalar dependencias:
    ```
    pip install -r requirements.txt
    ```
3. Migrar la base de datos:
    ```
    python manage.py makemigrations
    python manage.py migrate
    ```
4. Levantar el servidor:
    ```
    python manage.py runserver
    ```
5. Acceder en [http://localhost:8000](http://localhost:8000)

---

## Funciones
- Alta, baja, edición de socios
- Historial de pagos mensuales
- Búsqueda y filtrado
- Exportar a Excel
- Diseño minimalista (Bootstrap)
