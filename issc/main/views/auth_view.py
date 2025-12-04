from django.http import HttpResponse,JsonResponse
from django.template import loader
from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required

from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator

from ..models import AccountRegistration, IncidentReport, VehicleRegistration

from .utils import paginate

from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth.views import PasswordResetView
from django.contrib import messages
from django.core.mail import send_mail, BadHeaderError, get_connection
from django.conf import settings

import pandas as pd
from datetime import datetime


def login(request):
    template = loader.get_template('login.html')
    context = {}
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        # print(email)
        # print(password)
        user = authenticate(request, username=username,password=password)
        if user:
            auth_login(request, user)
            return redirect('dashboard') 

    return HttpResponse(template.render(context,request))



# @login_required(login_url='/login/')
def signup(request):
    user = AccountRegistration.objects.filter(username=request.user).values()

    users_list = AccountRegistration.objects.all().order_by('-date_joined')
    # users = paginate(users_list,request)


    template = loader.get_template('signup.html')
    context = {
        'user_role': user[0]['privilege'],
        'user_data':user[0],
        'users':users_list
    }

    if request.method == 'POST':
        username = request.POST.get('username')
        if 'delete' in request.POST:
            # Handle delete action
            user = AccountRegistration.objects.get(username=username)
            user.delete()
            return redirect('signup')  # Redirect to the same page after deleting

        if 'update' in request.POST:
            # Handle update action (you can collect and update data as needed)
            user = AccountRegistration.objects.get(username=username)
            new_email = request.POST.get('email')
            new_id_number = request.POST.get('id_number')
            
            # Check for duplicate email (excluding current user)
            if AccountRegistration.objects.filter(email=new_email).exclude(username=username).exists():
                messages.error(request, f"An account with the email '{new_email}' already exists. Please use a different email address.")
                return redirect('signup')
            
            # Check for duplicate ID number (excluding current user)
            if AccountRegistration.objects.filter(id_number=new_id_number).exclude(username=username).exists():
                messages.error(request, f"An account with the ID number '{new_id_number}' already exists. Please use a different ID number.")
                return redirect('signup')
            
            try:
                user.first_name = request.POST.get('first_name')
                user.middle_name = request.POST.get('middle_name')
                user.last_name = request.POST.get('last_name')
                user.email = new_email
                user.id_number = new_id_number
                user.contact_number = request.POST.get('contact_number')
                user.gender = request.POST.get('gender')
                user.department = request.POST.get('department')
                user.privilege = request.POST.get('privilege')
                user.status = request.POST.get('status')
                user.save()
                messages.success(request, 'Account updated successfully!')
                print('')
                return redirect('signup')  # Redirect to the same page after updating
            except Exception as e:
                messages.error(request, f"An error occurred while updating the account: {str(e)}")
                return redirect('signup')
    return HttpResponse(template.render(context,request))

def signup_forms(request):
    template = loader.get_template('signup_form.html')
    user = AccountRegistration.objects.filter(username=request.user).values()
    context = {
        'user_role': user[0]['privilege'],
        'user_data':user[0],
    }
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        id_number = request.POST.get('id_number')
        contact_number = request.POST.get('contact_number')
        gender = request.POST.get('gender')
        department = request.POST.get('department')
        privilege = request.POST.get('privilege')
        status = request.POST.get('status')
        password = request.POST.get('password')

        print(password)

        # Check for duplicate email
        if AccountRegistration.objects.filter(email=email).exists():
            context['error'] = f"An account with the email '{email}' already exists. Please use a different email address."
            context['form_data'] = request.POST
            return HttpResponse(template.render(context, request))
        
        # Check for duplicate ID number
        if AccountRegistration.objects.filter(id_number=id_number).exists():
            context['error'] = f"An account with the ID number '{id_number}' already exists. Please use a different ID number."
            context['form_data'] = request.POST
            return HttpResponse(template.render(context, request))
        
        # Check for duplicate username
        if AccountRegistration.objects.filter(username=username).exists():
            context['error'] = f"An account with the username '{username}' already exists. Please use a different username."
            context['form_data'] = request.POST
            return HttpResponse(template.render(context, request))

        try:
            user = AccountRegistration(
                username=username,
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                email=email,
                id_number=id_number,
                contact_number=contact_number,
                gender=gender,
                department=department,
                privilege=privilege,
                status=status,
                password=password
            )

            user.set_password(password)
            user.save()
            messages.success(request, 'Account created successfully!')
            # Send notification email to the newly created user with their credentials
            try:
                subject = 'Your ISSC account has been created'
                message = (
                    "Login to the ISSC account using the credentials saved:\n\n"
                    f"Username: {username}\n"
                    f"Password: {password}\n\n"
                    "You can login at: " + request.build_absolute_uri('/login/')
                )
                from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', settings.EMAIL_HOST_USER)

                # Log which sending account is being used (do not log the full password)
                try:
                    masked_pwd_info = f"{'*' * 4} (length={len(settings.EMAIL_HOST_PASSWORD)})" if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'not set'
                except Exception:
                    masked_pwd_info = 'not available'
                print(f"Attempting to send email using host={getattr(settings,'EMAIL_HOST','')}, user={getattr(settings,'EMAIL_HOST_USER','')} pwd={masked_pwd_info}")

                # Create an explicit connection using current settings so credentials are clear
                connection = get_connection(
                    host=getattr(settings, 'EMAIL_HOST', None),
                    port=getattr(settings, 'EMAIL_PORT', None),
                    username=getattr(settings, 'EMAIL_HOST_USER', None),
                    password=getattr(settings, 'EMAIL_HOST_PASSWORD', None),
                    use_tls=getattr(settings, 'EMAIL_USE_TLS', False),
                )

                send_mail(subject, message, from_email, [email], connection=connection, fail_silently=False)
            except BadHeaderError:
                print('Invalid header found when sending account creation email')
            except Exception as e:
                # Log the error server-side and show a non-blocking message
                print(f"Failed sending account creation email to {email}: {e}")
            return redirect('signup-forms')
        except Exception as e:
            context['error'] = f"An error occurred while creating the account: {str(e)}"
            context['form_data'] = request.POST
            return HttpResponse(template.render(context, request))
    return HttpResponse(template.render(context,request))

def logout(request):
    auth_logout(request)
    return redirect('login')

def import_data(request):
    template = loader.get_template('import.html')
    context = {}

    if request.method == 'POST':
        import_type = request.POST.get('import_type')
        excel_file = request.FILES.get('excel_file')
        print(import_type)

        if not import_type:
            context['error'] = "Please select an import type."
        elif not excel_file:
            context['error'] = "Please select an Excel file."
        else:
            try:
                df = pd.read_excel(excel_file)

                print(import_type=='user')

                if import_type == "user":
                    print("Reached import_data view")  # Debug
                    success_count = 0
                    error_count = 0
                    errors = []
                    
                    for index, row in df.iterrows():
                        try:
                            email = row['email']
                            id_number = row['ID Number']
                            
                            # Check for duplicate email
                            if AccountRegistration.objects.filter(email=email).exists():
                                error_msg = f"Row {index + 2}: Email '{email}' already exists"
                                errors.append(error_msg)
                                print(error_msg)
                                error_count += 1
                                continue
                            
                            # Check for duplicate ID number
                            if AccountRegistration.objects.filter(id_number=id_number).exists():
                                error_msg = f"Row {index + 2}: ID Number '{id_number}' already exists"
                                errors.append(error_msg)
                                print(error_msg)
                                error_count += 1
                                continue
                            
                            user = AccountRegistration(
                                username=id_number,
                                first_name=row['First Name'],
                                middle_name=row['Middle Name'],
                                last_name=row['Last Name'],
                                email=email,
                                id_number=id_number,
                                contact_number=row['contact number'],
                                gender={'Male': 'M', 'Female': 'F', 'Others': 'O'}.get(row['gender'], 'O'),
                                department=row['department'],
                                privilege=row['priv'],
                                status='allowed',
                            )
                            user.set_password('password')
                            user.save()
                            print(f"Saved User: {row['First Name']} - {id_number}")
                            success_count += 1
                        except Exception as inner_e:
                            error_msg = f"Row {index + 2}: {str(inner_e)}"
                            errors.append(error_msg)
                            print(f"Error saving user row {index + 2}: {inner_e}")
                            error_count += 1

                    if success_count > 0:
                        context['message'] = f"User data import completed! Successfully imported: {success_count} records."
                    if error_count > 0:
                        context['error'] = f"Failed to import {error_count} records. Errors: " + "; ".join(errors[:5])
                        if len(errors) > 5:
                            context['error'] += f"... and {len(errors) - 5} more errors."

                elif import_type == "vehicle":
                    success_count = 0
                    error_count = 0
                    errors = []
                    
                    for index, row in df.iterrows():
                        try:
                            email = row['email']
                            id_number = row['ID Number']
                            plate_number = row['plate_number']
                            sticker_number = row['sticker_number']
                            drivers_license = row['drivers_license']
                            
                            # Check for duplicate email
                            if VehicleRegistration.objects.filter(email_address=email).exists():
                                error_msg = f"Row {index + 2}: Email '{email}' already exists"
                                errors.append(error_msg)
                                print(error_msg)
                                error_count += 1
                                continue
                            
                            # Check for duplicate ID number
                            if VehicleRegistration.objects.filter(id_number=id_number).exists():
                                error_msg = f"Row {index + 2}: ID Number '{id_number}' already exists"
                                errors.append(error_msg)
                                print(error_msg)
                                error_count += 1
                                continue
                            
                            # Check for duplicate plate number
                            if VehicleRegistration.objects.filter(plate_number=plate_number).exists():
                                error_msg = f"Row {index + 2}: Plate Number '{plate_number}' already exists"
                                errors.append(error_msg)
                                print(error_msg)
                                error_count += 1
                                continue
                            
                            # Check for duplicate sticker number
                            if VehicleRegistration.objects.filter(sticker_number=sticker_number).exists():
                                error_msg = f"Row {index + 2}: Sticker Number '{sticker_number}' already exists"
                                errors.append(error_msg)
                                print(error_msg)
                                error_count += 1
                                continue
                            
                            # Check for duplicate driver's license
                            if VehicleRegistration.objects.filter(drivers_license=drivers_license).exists():
                                error_msg = f"Row {index + 2}: Driver's License '{drivers_license}' already exists"
                                errors.append(error_msg)
                                print(error_msg)
                                error_count += 1
                                continue
                            
                            vehicle = VehicleRegistration(
                                first_name=row['First Name'],
                                middle_name=row['Middle Name'],
                                last_name=row['Last Name'],
                                id_number=id_number,
                                contact_number=row['contact number'],
                                email_address=email,
                                role=row['role'],
                                vehicle_type=row['vehicle_type'],
                                color=row['color'],
                                model=row['model'],
                                plate_number=plate_number,
                                sticker_number=sticker_number,
                                drivers_license=drivers_license,
                                guardian_name=row['guardian_name'],
                                guardian_number=row['guardian_contact'],
                                status='allowed',
                                image=None,
                                qr_code=None,
                                is_archived=False
                            )
                            vehicle.save()
                            print(f"Saved Vehicle: {plate_number}")
                            success_count += 1
                        except Exception as inner_e:
                            error_msg = f"Row {index + 2}: {str(inner_e)}"
                            errors.append(error_msg)
                            print(f"Error saving vehicle row {index + 2}: {inner_e}")
                            error_count += 1

                    if success_count > 0:
                        context['message'] = f"Vehicle data import completed! Successfully imported: {success_count} records."
                    if error_count > 0:
                        context['error'] = f"Failed to import {error_count} records. Errors: " + "; ".join(errors[:5])
                        if len(errors) > 5:
                            context['error'] += f"... and {len(errors) - 5} more errors."

                else:
                    context['error'] = "Invalid import type selected."

            except Exception as e:
                context['error'] = f"Error processing Excel file: {str(e)}"
                print(f"Error processing Excel file: {str(e)}")

    return HttpResponse(template.render(context, request))



def getUser(request):
    # New format: username and id_number should be <privilege><4-digit counter>
    # e.g. admin0001, faculty0001, student0001
    user_type = request.GET.get('type', '').strip().lower()
    if user_type not in ['student', 'faculty', 'admin']:
        return JsonResponse({'error': 'Invalid or missing user type'}, status=400)

    # Find the latest username for this privilege and increment numeric suffix
    prefix = f"{user_type}"
    latest = (
        AccountRegistration.objects.filter(
            username__istartswith=prefix,
            privilege__iexact=user_type
        )
        .order_by('-username')
        .values('username')
        .first()
    )

    if latest and latest.get('username'):
        latest_username = latest['username']
        # Extract numeric suffix after the prefix
        suffix = latest_username[len(prefix):]
        try:
            next_num = int(''.join(filter(str.isdigit, suffix))) + 1
        except (ValueError, TypeError):
            next_num = 1
    else:
        next_num = 1

    new_suffix = str(next_num).zfill(4)
    new_username = f"{prefix}{new_suffix}"

    # Use same value for id_number as requested
    new_id = new_username
    return JsonResponse({'id_number': new_id, 'username': new_username})

# def password_reset(request):
#     if request.method == "POST":
#         email = request.POST.get("email")  # Get the email from the form
#         form = PasswordResetForm({"email": email})

#         if form.is_valid():
#             form.save(
#                 request=request,
#                 use_https=request.is_secure(),
#                 email_template_name="registration/password_reset_email.html"
#             )
#             messages.success(request, "A password reset link has been sent to your email.")
#             return redirect("password_reset_done")  # Redirect to a confirmation page

#         else:
#             messages.error(request, "Invalid email address. Please try again.")

#     else:
#         form = PasswordResetForm()

#     return render(request, "test.html")


from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from .forms import CustomPasswordResetForm, CustomSetPasswordForm

class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'registration/acc_reset.html'
    form_class = CustomPasswordResetForm
    email_template_name = 'registration/acc_reset_email.html'
    success_url = reverse_lazy('password_reset_done')

class CustomPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'registration/acc_reset_done.html'

class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'registration/acc_reset_confirm.html'
    form_class = CustomSetPasswordForm
    success_url = reverse_lazy('password_reset_complete')

class CustomPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'registration/acc_reset_complete.html'
