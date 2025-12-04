from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.mail import send_mail, BadHeaderError
from django.conf import settings

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a test AccountRegistration and send the account notification email.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=False, help='Username for the test account', default='testuser001')
        parser.add_argument('--email', required=False, help='Email for the test account', default='vinceerickquiozon14@gmail.com')
        parser.add_argument('--password', required=False, help='Password for the test account', default='TestPass123!')
        parser.add_argument('--delete-if-exists', action='store_true', help='Delete existing user with same username/email before creating')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        delete_if_exists = options['delete_if_exists']

        # Delete existing user if requested
        existing = User.objects.filter(username=username) | User.objects.filter(email=email)
        if existing.exists():
            if delete_if_exists:
                existing.delete()
                self.stdout.write(self.style.WARNING('Deleted existing user(s) with same username or email.'))
            else:
                self.stdout.write(self.style.ERROR('User with same username or email already exists. Use --delete-if-exists to overwrite.'))
                return

        try:
            user = User(
                username=username,
                first_name='Test',
                middle_name='T',
                last_name='User',
                email=email,
                id_number=username,
                contact_number='0000000000',
                gender='O',
                department='Testing',
                privilege='student',
                status='allowed'
            )
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Created user {username} ({email})'))

            # Send notification email similar to signup_forms
            subject = 'Your ISSC account has been created'
            message = (
                "Login to the ISSC account using the credentials saved:\n\n"
                f"Username: {username}\n"
                f"Password: {password}\n\n"
                "You can login at: " + 'http://localhost:8000/login/'
            )
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)
            try:
                send_mail(subject, message, from_email, [email], fail_silently=False)
                self.stdout.write(self.style.SUCCESS(f'Notification email sent to {email}'))
            except BadHeaderError:
                self.stdout.write(self.style.ERROR('Invalid header found when sending email'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Failed to send notification email: {e}'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating test user: {e}'))
