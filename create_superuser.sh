if [[ -n "$CREATE_SUPER_USER" ]]; then
echo "==> Creating super user"

printf "from base.models import ResUsers\nif not ResUsers.objects.exists(): ResUsers.objects.create_superuser(*'$CREATE_SUPER_USER'.split(':'))" | python manage.py shell

echo "from django.contrib.auth.models import User; User.objects.create_superuser('admin', 'admin@example.com', 'pass')" | python manage.py shell
fi

