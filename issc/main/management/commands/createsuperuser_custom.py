from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import getpass
import sys

User = get_user_model()

class Command(BaseCommand):
    help = 'Create a superuser with all required custom fields'

    def add_arguments(self, parser):
        parser.add_argument('--username', help='Username for the superuser')
        parser.add_argument('--email', help='Email for the superuser')
        parser.add_argument('--password', help='Password for the superuser')
        parser.add_argument('--first-name', help='First name')
        parser.add_argument('--last-name', help='Last name')
        parser.add_argument('--middle-name', help='Middle name', default='')
        parser.add_argument('--id-number', help='ID number', default='ADMIN001')
        parser.add_argument('--contact-number', help='Contact number', default='000-000-0000')
        parser.add_argument('--gender', choices=['M', 'F', 'O'], help='Gender (M/F/O)', default='M')
        parser.add_argument('--department', help='Department', default='Administration')
        parser.add_argument('--no-input', action='store_true', help='Run non-interactively with defaults')

    def handle(self, *args, **options):
        if options['no_input']:
            # Non-interactive mode with defaults
            username = options['username'] or 'admin'
            email = options['email'] or 'admin@issc.local'
            password = options['password'] or 'admin123'
            first_name = options['first_name'] or 'System'
            last_name = options['last_name'] or 'Administrator'
            middle_name = options['middle_name'] or ''
            id_number = options['id_number'] or 'ADMIN001'
            contact_number = options['contact_number'] or '000-000-0000'
            gender = options['gender'] or 'M'
            department = options['department'] or 'Administration'
        else:
            # Interactive mode
            username = options['username'] or input('Username: ') or 'admin'
            email = options['email'] or input('Email: ') or 'admin@issc.local'
            
            if options['password']:
                password = options['password']
            else:
                password = getpass.getpass('Password: ')
                if not password:
                    password = 'admin123'
                    self.stdout.write(self.style.WARNING('Using default password: admin123'))

            first_name = options['first_name'] or input('First name: ') or 'System'
            last_name = options['last_name'] or input('Last name: ') or 'Administrator'
            middle_name = options['middle_name'] or input('Middle name (optional): ') or ''
            id_number = options['id_number'] or input('ID number (default: ADMIN001): ') or 'ADMIN001'
            contact_number = options['contact_number'] or input('Contact number (default: 000-000-0000): ') or '000-000-0000'
            
            gender_input = input('Gender (M/F/O, default: M): ').upper()
            gender = gender_input if gender_input in ['M', 'F', 'O'] else 'M'
            
            department = options['department'] or input('Department (default: Administration): ') or 'Administration'

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.ERROR(f'User with username "{username}" already exists!'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'User with email "{email}" already exists!'))
            return

        if User.objects.filter(id_number=id_number).exists():
            self.stdout.write(self.style.ERROR(f'User with ID number "{id_number}" already exists!'))
            return

        try:
            # Create the superuser
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                middle_name=middle_name,
                id_number=id_number,
                contact_number=contact_number,
                gender=gender,
                department=department,
                privilege='admin',
                status='allowed'
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser "{username}" created successfully!\n'
                    f'Email: {email}\n'
                    f'Name: {first_name} {middle_name} {last_name}\n'
                    f'ID: {id_number}\n'
                    f'Department: {department}'
                )
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating superuser: {str(e)}'))
            sys.exit(1)
