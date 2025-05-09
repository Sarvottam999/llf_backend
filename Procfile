web: gunicorn llf_backend.wsgi --log-file - 
#or works good with external database
web: python manage.py migrate && gunicorn llf_backend.wsgi
