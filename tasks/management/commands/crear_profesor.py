from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Crea un usuario con rol de Profesor"

    def add_arguments(self, parser):
        parser.add_argument("username", type=str, help="Nombre de usuario")
        parser.add_argument("email", type=str, help="Correo electrónico")
        parser.add_argument(
            "password", type=str, help="Contraseña del usuario"
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f"El usuario {username} ya existe"))
            return

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=User.Roles.PROFESOR,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Profesor creado exitosamente: {username}")
        )