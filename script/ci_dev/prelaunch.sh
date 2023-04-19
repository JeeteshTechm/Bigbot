#!/usr/bin/bash
source /d/Environments/bigbot-env/Scripts/activate
export DATABASE_NAME=postgres
export DATABASE_PASSWORD=foo
export DATABASE_USER=postgres
export IS_DEVELOPMENT=True

py manage.py makemigrations
py manage.py migrate
# py manage.py createsuperuser