from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from ..models import AccountRegistration, IncidentReport, VehicleRegistration

import calendar
import pandas as pd
from django.utils.timezone import now
from collections import Counter

from django.db.models import Count
from django.utils import timezone

from django.template.loader import render_to_string
# import pdfkit  # Temporarily commented out

def incident_rate(selected_year=None):
    if selected_year is None:
        selected_year = now().year
    
    reports = IncidentReport.objects.filter(date__year=selected_year)

    # Count incidents per month
    incident_counts = Counter(report.date.month for report in reports)

    # Show all 12 months for complete graph
    months = list(range(1, 13))
    counts = [incident_counts.get(m, 0) for m in months]

    # Calculate percentage increase
    percentage_increase = [0]  # First month has no previous data
    for i in range(1, len(counts)):
        prev = counts[i - 1]
        current = counts[i]
        if prev == 0:  # Prevent division by zero
            percentage = 0 if current == 0 else 100
        else:
            percentage = ((current - prev) / prev) * 100
        percentage_increase.append(round(percentage, 2))

    # Return raw data
    return {
        "months": [calendar.month_abbr[m] for m in months],
        "incident_counts": counts,
        "percentage_increase": percentage_increase
    }

def incident_status_breakdown(selected_year=None):
    """Get current breakdown of incidents by status"""
    if selected_year is None:
        selected_year = now().year
    
    reports = IncidentReport.objects.filter(date__year=selected_year, is_archived=False)
    
    status_counts = Counter(report.status for report in reports)
    
    return {
        "statuses": ['Open', 'Pending', 'Closed'],
        "counts": [
            status_counts.get('open', 0),
            status_counts.get('pending', 0),
            status_counts.get('closed', 0)
        ],
        "total": sum(status_counts.values())
    }

def monthly_status_trends(selected_year=None):
    """Get monthly trends for open and pending cases"""
    if selected_year is None:
        selected_year = now().year
    
    # Show all 12 months for complete graph
    months = list(range(1, 13))
    
    open_counts = []
    pending_counts = []
    closed_counts = []
    
    for month in months:
        reports = IncidentReport.objects.filter(
            date__year=selected_year,
            date__month=month,
            is_archived=False
        )
        open_counts.append(reports.filter(status='open').count())
        pending_counts.append(reports.filter(status='pending').count())
        closed_counts.append(reports.filter(status='closed').count())
    
    return {
        "months": [calendar.month_abbr[m] for m in months],
        "open_cases": open_counts,
        "pending_cases": pending_counts,
        "closed_cases": closed_counts
    }

def resolution_time_analysis(selected_year=None):
    """Analyze average resolution times"""
    if selected_year is None:
        selected_year = now().year
    
    # Show all 12 months for complete graph
    months = list(range(1, 13))
    
    avg_resolution_days = []
    
    for month in months:
        closed_reports = IncidentReport.objects.filter(
            date__year=selected_year,
            date__month=month,
            status='closed',
            is_archived=False
        )
        
        if closed_reports.exists():
            total_days = 0
            count = 0
            for report in closed_reports:
                days_to_close = (report.last_updated.date() - report.date).days
                total_days += days_to_close
                count += 1
            avg_resolution_days.append(round(total_days / count, 1) if count > 0 else 0)
        else:
            avg_resolution_days.append(0)
    
    return {
        "months": [calendar.month_abbr[m] for m in months],
        "avg_days": avg_resolution_days
    }



def monthly_incident_graph(selected_year=None):
    if selected_year is None:
        selected_year = now().year
        
    incidents = IncidentReport.objects.filter(date__year=selected_year)
    
    # Get all 12 months for complete visualization
    all_months = list(calendar.month_name)[1:]
    
    if incidents.exists():
        months = [incident.date.strftime('%B') for incident in incidents]
        month_counts = Counter(months)
        incident_data = [month_counts.get(month, 0) for month in all_months]
    else:
        incident_data = [0] * 12

    # Return raw data
    return {
        "months": all_months,
        "incident_data": incident_data
    }






def department_incident_graph():
    incidents = IncidentReport.objects.all()
    if not incidents.exists():
        return None

    departments = [incident.department for incident in incidents]

    # Count incidents per department
    department_counts = Counter(departments)
    department_names = list(department_counts.keys())
    incident_data = list(department_counts.values())

    # Return raw data
    return {
        "department_names": department_names,
        "incident_data": incident_data
    }

def vehicle_graph():
    data = VehicleRegistration.objects.values('role', 'vehicle_type')

    if not data.exists():  # Check if the queryset is empty
        return None

    df = pd.DataFrame(list(data))

    if df.empty:  # Additional safeguard if DataFrame is empty
        return None

    counts = df.groupby(['role', 'vehicle_type']).size().unstack(fill_value=0)

    # Return raw data
    return {
        "roles": counts.columns.tolist(),
        "vehicle_types": counts.index.tolist(),
        "counts": counts.values.tolist()
    }


def incident_type(selected_month=None):
    current_year = timezone.now().year
    queryset = IncidentReport.objects.filter(is_archived=False, date__year=current_year)

    if selected_month:
        try:
            # Extract the month part from 'YYYY-MM'
            month_number = int(selected_month.split("-")[1])
            queryset = queryset.filter(date__month=month_number)
        except (IndexError, ValueError):
            pass  # fallback if format is wrong

    monthly_subjects = (
        queryset.values('subject')
        .annotate(count=Count('subject'))
        .order_by('-count')
    )

    subjects = [entry['subject'] for entry in monthly_subjects]
    counts = [entry['count'] for entry in monthly_subjects]

    return {
        'subjects': subjects,
        'counts': counts
    }

def plot_monthly_incidents(data):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(data['months'], data['incident_data'], color='#800000')
    ax.set_title('Monthly Incidents')
    ax.set_ylabel('Number of Incidents')
    ax.set_xlabel('Month')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def plot_incident_type(data):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(data['subjects'], data['counts'], color='#d63031')
    ax.set_title('Incident Type Count')
    ax.set_ylabel('Number of Incidents')
    ax.set_xlabel('Incident Type')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

def plot_incident_rate(data):
    fig, ax1 = plt.subplots(figsize=(10, 5))

    ax1.set_xlabel('Month')
    ax1.set_ylabel('Total Incidents', color='#800000')
    ax1.plot(data['months'], data['incident_counts'], color='#800000', marker='o', label='Total Incidents')
    ax1.tick_params(axis='y', labelcolor='#800000')

    ax2 = ax1.twinx()
    ax2.set_ylabel('% Increase', color='#d63031')
    ax2.plot(data['months'], data['percentage_increase'], color='#d63031', linestyle='--', marker='x', label='% Increase')
    ax2.tick_params(axis='y', labelcolor='#d63031')

    fig.suptitle('Incident Trends')
    fig.tight_layout()
    return fig

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)  # Free memory
    return image_base64


@login_required(login_url='/login/')
def base(request):
    # Use get_object_or_404 to ensure a valid user is retrieved
    user = get_object_or_404(AccountRegistration, username=request.user.username)

    # If the user is not authenticated, redirect (though it's redundant because of the decorator)
    if not request.user.is_authenticated:
        return redirect('login')

    if user.privilege == 'student':
        return redirect('about')

    # Get filter parameters
    selected_year = request.GET.get('year')
    selected_month = request.GET.get('month')
    
    # Convert year to int if provided, otherwise use current year
    if selected_year:
        try:
            selected_year = int(selected_year)
        except ValueError:
            selected_year = now().year
    else:
        selected_year = now().year
    
    # Get available years for filter dropdown
    years = IncidentReport.objects.dates('date', 'year', order='DESC')
    available_years = [date.year for date in years]
    if not available_years:
        available_years = [now().year]

    monthly_incident_data = monthly_incident_graph(selected_year)
    department_incident_data = department_incident_graph()
    vehicle_data = vehicle_graph()
    incident_data = incident_rate(selected_year)
    incident_subject = incident_type(selected_month)

    # Pass the image data along with other context variables
    context = {
        'user_role': user.privilege,  
        'user_data': user,
        'monthly_incident_data': monthly_incident_data,
        'department_incident_data': department_incident_data,
        'vehicle_data': vehicle_data,
        'incident_data': incident_data,
        'incident_type': incident_subject,
        'selected_month': selected_month or '',
        'selected_year': selected_year,
        'available_years': available_years,
        'status_breakdown': incident_status_breakdown(selected_year),
        'status_trends': monthly_status_trends(selected_year),
        'resolution_analysis': resolution_time_analysis(selected_year)
    }

    print(incident_subject)
    # Render the template with the context
    return render(request, 'dashboard/dashboard.html', context)

