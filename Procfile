web: python manage.py migrate && python manage.py collectstatic --noinput && gunicorn grua_platform.wsgi:application --bind 0.0.0.0:$PORT
