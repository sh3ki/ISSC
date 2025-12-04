from django.core.management.base import BaseCommand
from django.core.mail import send_mail, get_connection
from django.conf import settings


class Command(BaseCommand):
    help = 'Send a test email using the current EMAIL settings to verify SMTP connectivity.'

    def add_arguments(self, parser):
        parser.add_argument('--to', dest='to', required=True, help='Recipient email address to send the test message to')
        parser.add_argument('--subject', dest='subject', default='ISSC test email', help='Subject for the test email')
        parser.add_argument('--body', dest='body', default='This is a test email from the ISSC application.', help='Body for the test email')
        parser.add_argument('--use-local-backend', dest='use_local', action='store_true', help='Use local (console/locmem) backend instead of SMTP')

    def handle(self, *args, **options):
        to_addr = options['to']
        subject = options['subject']
        body = options['body']
        use_local = options['use_local']

        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', getattr(settings, 'EMAIL_HOST_USER', None))
        if not from_email:
            self.stdout.write(self.style.ERROR('No from email configured (DEFAULT_FROM_EMAIL or EMAIL_HOST_USER).'))
            return

        self.stdout.write(f'Using from: {from_email}')
        if use_local:
            self.stdout.write('Using local/console email backend for test (no real SMTP connection).')
            # Temporarily use locmem backend
            connection = get_connection('django.core.mail.backends.locmem.EmailBackend')
        else:
            self.stdout.write('Using configured SMTP backend.')
            connection = get_connection()  # uses settings

        try:
            send_mail(subject, body, from_email, [to_addr], connection=connection, fail_silently=False)
            self.stdout.write(self.style.SUCCESS(f'Test email sent to {to_addr}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to send test email: {e}'))
            # Show helpful debug info
            try:
                self.stdout.write('SMTP host: ' + str(getattr(settings, 'EMAIL_HOST', 'not set')))
                self.stdout.write('SMTP port: ' + str(getattr(settings, 'EMAIL_PORT', 'not set')))
                self.stdout.write('EMAIL_HOST_USER: ' + str(getattr(settings, 'EMAIL_HOST_USER', 'not set')))
            except Exception:
                pass
