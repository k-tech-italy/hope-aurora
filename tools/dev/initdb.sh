#!/bin/bash

### ND: needspgpass to be setup
DB_ENGINE=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['ENGINE'])"`
DB_HOST=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['HOST'])"`
DB_PORT=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['PORT'], end='')"`
DB_NAME=`python manage.py shell --no-imports -c "from django.conf import settings; print(settings.DATABASES['default']['NAME'], end='')"`

echo initializing ${DB_ENGINE} database ${DB_NAME}
dropdb -h ${DB_HOST} -p ${DB_PORT} -U postgres -f --if-exists "${DB_NAME}"
dropdb -h ${DB_HOST} -p ${DB_PORT} -U postgres -f --if-exists "test_${DB_NAME}"
createdb -h ${DB_HOST} -p ${DB_PORT} -U postgres ${DB_NAME} || echo "Reusing DB ${DB_NAME}"
./manage.py upgrade --organization ktech --admin-password ${ADMIN_PASSWORD}  --admin-email admin@example.com
#DJANGO_SUPERUSER_PASSWORD=123 ./manage.py createsuperuser --username admin --email a@a.com --noinput
