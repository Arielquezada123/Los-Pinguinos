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

# Ejecutar Daphne
echo "Iniciando Daphne (ASGI server)..."
exec daphne -b 0.0.0.0 -p 8000 watermilimiter.asgi:application
