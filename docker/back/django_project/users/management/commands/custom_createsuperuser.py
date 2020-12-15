from django.contrib.auth.management.commands import createsuperuser
from django.core.management import CommandError
from users.models import User


class Command(createsuperuser.Command):
    help = 'Create a superuser with a password non-interactively'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--password', dest='password', default=None,
            help='Specifies the password for the superuser.',
        )

    def handle(self, *args, **options):
        options.setdefault('interactive', False)
        email = options.get('email')
        password = options.get('password')

        if not (email and password):
            raise CommandError(' --email and --password are required options')

        user_data = {
            'email': email,
            'password': password,
        }

        exists = User.objects.filter(email=email).exists()
        if not exists:
            User.objects.create_superuser(**user_data)
            print(f"------------ created superuser {email} ! ------------")
        else:
            print("this email already exists")
