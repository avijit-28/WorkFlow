release: python manage.py migrate --noinput
web: gunicorn taskmanager.wsgi --log-file - --bind 0.0.0.0:$PORT
