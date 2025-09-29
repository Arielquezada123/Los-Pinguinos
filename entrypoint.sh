#!/bin/sh
python manage.py collectstatic --noinput
chown -R 101:101 /pinguinos/staticfiles/
chown -R 101:101 /pinguinos/media/
exec uwsgi --ini uwsgi/start_uwsgi.ini