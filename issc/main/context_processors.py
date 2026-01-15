from django.db.models import Q

from .models import AccountRegistration, IncidentReport


def incident_notifications(request):
    """Expose incident notification counts for the current user.

    Admins see all open, non-archived incidents. Faculty see open incidents
    within their department. Students see their own open incidents. This keeps
    the badge honest without affecting existing view logic.
    """
    new_incident_count = 0
    has_new_incident_notifications = False

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "new_incident_count": new_incident_count,
            "has_new_incident_notifications": has_new_incident_notifications,
        }

    account = AccountRegistration.objects.filter(username=user).first()
    if not account:
        return {
            "new_incident_count": new_incident_count,
            "has_new_incident_notifications": has_new_incident_notifications,
        }

    # Only count brand-new incidents (still open, not archived) that have not yet been
    # touched by an admin (last_updated_by blank) AND that the current admin can validate
    # (not part of faculty_involved).
    incident_qs = IncidentReport.objects.filter(
        status="open",
        is_archived=False,
    ).filter(Q(last_updated_by__isnull=True) | Q(last_updated_by=""))

    if account.privilege == "faculty":
        incident_qs = incident_qs.filter(department__iexact=account.department).exclude(faculty_involved=account)
    elif account.privilege == "student":
        incident_qs = incident_qs.filter(id_number=account.id_number)
    else:  # admin
        incident_qs = incident_qs.exclude(faculty_involved=account)

    new_incident_count = incident_qs.count()
    has_new_incident_notifications = new_incident_count > 0

    return {
        "new_incident_count": new_incident_count,
        "has_new_incident_notifications": has_new_incident_notifications,
    }
