#!/bin/bash
echo ------------ migration start ------------
python3 manage.py makemigrations
python3 manage.py migrate
echo ------------ migration end ------------
# echo start loading dump data
# python3 manage.py loaddata dump.json
# echo end loading dump data
python3 manage.py collectstatic --no-input
python3 manage.py custom_createsuperuser --email admin@example.com --password prescription
# gunicorn config.wsgi:application --timeout 120 --bind 0.0.0.0:8083
