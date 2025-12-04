from django.http import HttpResponse
from django.template import loader
from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required

from django.core.files.storage import FileSystemStorage
from django.core.paginator import Paginator

from ..models import AccountRegistration, IncidentReport, VehicleRegistration, IncidentUpdate

from .utils import paginate

from django.template.loader import render_to_string
# import pdfkit  # Temporarily commented out

@login_required(login_url='/login/')
def incident(request):
    user = AccountRegistration.objects.filter(username=request.user).values()
    is_archived = request.GET.get('archive', 'false').lower() == 'true'
    if user[0]['privilege'] == 'student':
        template = loader.get_template('incident/student/incident.html')
        open_incident = IncidentReport.objects.filter(status='open', id_number=user[0]['id_number'] , is_archived=is_archived).order_by('date_joined')
        pending_incident = IncidentReport.objects.filter(status='pending', id_number=user[0]['id_number'] , is_archived=is_archived).order_by('date_joined')
        closed_incident = IncidentReport.objects.filter(status='closed', id_number=user[0]['id_number'] , is_archived=is_archived).order_by('date_joined')
    elif user[0]['privilege'] == 'faculty':
        template = loader.get_template('incident/faculty/incident.html')
        user_department = user[0]['department']
        open_incident = IncidentReport.objects.filter(status='open', department__iexact=user_department, is_archived=is_archived).order_by('date_joined')
        pending_incident = IncidentReport.objects.filter(status='pending', department__iexact=user_department, is_archived=is_archived).order_by('date_joined')
        closed_incident = IncidentReport.objects.filter(status='closed', department__iexact=user_department, is_archived=is_archived).order_by('date_joined')
    else:
        template = loader.get_template('incident/admin/incident.html')
        open_incident = IncidentReport.objects.filter(status='open', is_archived=is_archived).order_by('date_joined')
        pending_incident = IncidentReport.objects.filter(status='pending', is_archived=is_archived).order_by('date_joined')
        closed_incident = IncidentReport.objects.filter(status='closed', is_archived=is_archived).order_by('date_joined')


    if request.method == 'POST':
        incident_id = request.POST.get('incident_id')
        incident = IncidentReport.objects.get(id=incident_id) if incident_id else None

       
        if 'delete' in request.POST:
            incident.is_archived = True
            incident.last_updated_by = user[0]['id_number']
            incident.save()
            return redirect('incidents')
            
        if 'update' in request.POST:
            status = request.POST['status']
            incident.status = status
            incident.last_updated_by = user[0]['id_number']
            incident.save()
            return redirect('incidents')

        if 'approve' in request.POST:
            incident.status = 'pending'
            incident.last_updated_by = user[0]['id_number']
            if hasattr(incident, 'invalidation_reason'):
                incident.invalidation_reason = None  # Clear any previous invalidation reason
            incident.save()
            return redirect('incidents')
            
        if 'invalidate' in request.POST:
            invalidate_reason = request.POST.get('invalidate_reason', '').strip()
            incident.status = 'closed'
            incident.last_updated_by = user[0]['id_number']
            if hasattr(incident, 'invalidation_reason'):
                incident.invalidation_reason = invalidate_reason
            incident.save()
            return redirect('incidents')
            
        if 'disapprove' in request.POST:
            incident.status = 'closed'
            incident.last_updated_by = user[0]['id_number']
            incident.save()
            return redirect('incidents')

        if 'restore' in request.POST:
            incident.is_archived = False
            incident.last_updated_by = user[0]['id_number']
            incident.save()
            return redirect('incidents')

    context = {
        'user_role': user[0]['privilege'],
        'user_data': user[0],
        'open_incident': open_incident,
        'pending_incident': pending_incident,
        'closed_incident': closed_incident,
        'is_archived': is_archived
    }

    return HttpResponse(template.render(context, request))

@login_required(login_url='/login/')
def incident_details(request, id):
    user = AccountRegistration.objects.filter(username=request.user).values()
    incident = get_object_or_404(IncidentReport, id=id)
    template = loader.get_template('incident/details.html')
    # Determine archive filter to keep counts consistent with this incident
    archive_flag = incident.is_archived if hasattr(incident, 'is_archived') else False

    # All incidents in the same archive state, ordered oldest->newest
    all_incidents_qs = IncidentReport.objects.filter(is_archived=archive_flag).order_by('date_joined', 'id')
    total_incidents = all_incidents_qs.count()

    # Position of this incident in the overall ordered list (oldest = 1)
    try:
        overall_index = list(all_incidents_qs.values_list('id', flat=True)).index(incident.id)
        incident_number = overall_index + 1
    except ValueError:
        incident_number = None

    # Counts per status and position within its status (oldest = 1)
    status_counts = {
        'open': IncidentReport.objects.filter(status='open', is_archived=archive_flag).count(),
        'pending': IncidentReport.objects.filter(status='pending', is_archived=archive_flag).count(),
        'closed': IncidentReport.objects.filter(status='closed', is_archived=archive_flag).count(),
    }

    status_qs = IncidentReport.objects.filter(status=incident.status, is_archived=archive_flag).order_by('date_joined', 'id')
    try:
        status_index = list(status_qs.values_list('id', flat=True)).index(incident.id)
        incident_status_number = status_index + 1
    except ValueError:
        incident_status_number = None

    context = {
        'incident': incident,
        'user_role': user[0]['privilege'],
        'user_data': user[0],
        'total_incidents': total_incidents,
        'incident_number': incident_number,
        'status_counts': status_counts,
        'incident_status_number': incident_status_number,
        'status_count_for_incident': status_counts.get(incident.status, 0),
    }

    if request.method == 'POST':
        # If the Update Case modal was submitted, create an IncidentUpdate
        if 'update_case' in request.POST:
            update_reason = request.POST.get('update_reason', '').strip()
            update_file = request.FILES.get('update_file')

            created_by = user[0]['id_number'] if user and user[0] else ''

            try:
                iu = IncidentUpdate(
                    incident=incident,
                    reason=update_reason,
                    created_by=created_by,
                )
                if update_file:
                    iu.file = update_file
                iu.save()

                # Update incident status from modal's status select (if provided)
                new_status = request.POST.get('status', incident.status)
                incident.status = new_status
                incident.last_updated_by = created_by
                incident.save()
            except Exception as e:
                print(f"Error saving IncidentUpdate: {e}")

            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Regular incident field updates (non-modal)
        status = request.POST['status']
        incident.last_updated_by = user[0]['id_number']
        incident.status = status
        incident.first_name = request.POST.get('first_name')
        incident.middle_name = request.POST.get('middle_name')
        incident.last_name = request.POST.get('last_name')
        incident.contact_number = request.POST.get('contact_number')
        incident.id_number = request.POST.get('id_number')
        incident.subject = request.POST.get('subject')
        # Save people_involved if present
        incident.people_involved = request.POST.get('people_involved')
        incident.location = request.POST.get('location')
        incident.incident = request.POST.get('incident')
        incident.request_for_action = request.POST.get('request_for_action')
        # If reported_by was submitted use it otherwise default to current user
        incident.reported_by = request.POST.get('reported_by', f"{user[0]['first_name']} {user[0]['last_name']}")
        incident.position = request.POST.get('position')
        incident.department = request.POST.get('department')
        # If phone_number submitted use it otherwise default to current user's contact
        incident.phone_number = request.POST.get('phone_number', user[0]['contact_number'])
        incident.save()

        return redirect(request.META.get('HTTP_REFERER', '/'))

    return HttpResponse(template.render(context, request))

@login_required(login_url='/login/')
def incident_print(request, id):
    user = AccountRegistration.objects.filter(username=request.user).values()
    incident = get_object_or_404(IncidentReport, id=id)
    context = {
        'incident': incident,
        'user_role': user[0]['privilege'],
        'user_data': user[0],
    }


    html_string = render_to_string('incident/print.html', context)
    # pdf_file = pdfkit.from_string(html_string, False)  # Temporarily commented out

    # Return HTML instead of PDF temporarily
    response = HttpResponse(html_string, content_type='text/html')
    # response['Content-Disposition'] = 'inline; filename="incident_{id}_report.pdf"'

    return response
@login_required(login_url='/login/')
def incident_forms(request):
    user = AccountRegistration.objects.filter(username=request.user).values()
    template = loader.get_template('incident/forms.html')

    context = {
        'user_role': user[0]['privilege'],
        'user_data': user[0]
    }

    if request.method == 'POST':
        first_name = request.POST['first_name']
        middle_name = request.POST.get('middle_name', '')  # Optional field
        last_name = request.POST['last_name']
        contact_number = request.POST['contact_number']
        id_number = request.POST['id_number']
        subject = request.POST.get('subject', '').strip()
        # If user selected "Other/s", allow a free-text value from subject_other
        if subject == 'Other/s':
            subject_other = request.POST.get('subject_other', '').strip()
            if subject_other:
                subject = subject_other
        location = request.POST['location']
        incident = request.POST['incident']
        people_involved = request.POST.get('people_involved', '').strip()
        request_for_action = request.POST['request_for_action']
        # Use current user's name and contact for reported_by and phone_number (fields removed from visible form)
        reported_by = f"{user[0]['first_name']} {user[0]['last_name']}"
        position = request.POST['position']
        department = request.POST['department']
        phone_number = user[0]['contact_number']
        # Always set status to 'open' for new incidents
        status = 'open'
        file = request.FILES.get('file', None)

        # Create and save the incident report manually
        report = IncidentReport(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            contact_number=contact_number,
            id_number=id_number,
            subject=subject,
            people_involved=people_involved,
            location=location,
            incident=incident,
            request_for_action=request_for_action,
            reported_by=reported_by,
            position=position,
            department=department,
            phone_number=phone_number,
            status=status,
            file=file,
            is_archived=False
        )
        report.save()

    return HttpResponse(template.render(context, request))
