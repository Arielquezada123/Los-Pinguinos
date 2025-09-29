#!/bin/sh

# Ir al directorio de Django
cd /pinguinos

# Crear directorios si no existen
mkdir -p /pinguinos/staticfiles /pinguinos/media

# Collect static files
echo "Collectando archivos estaticos con el SH.. pip pip pip pip "
python manage.py collectstatic --noinput

# Ejecutar migraciones
echo "Running migrations..."
python manage.py migrate

# Ejecutar uWSGI
exec uwsgi --ini /pinguinos/uwsgi/start_uwsgi.ini

