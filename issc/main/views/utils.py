from django.core.paginator import Paginator
from django.http import JsonResponse, Http404
from ..models import AccountRegistration


def paginate(queryset, request, per_page=5):
        paginator = Paginator(queryset, per_page)
        page = request.GET.get('page')
        return paginator.get_page(page)

def getUser(request):
    user_id = request.GET.get('id')
    if not user_id:
        return JsonResponse({'error': 'Missing user ID'}, status=400)
    
    try:
        user = AccountRegistration.objects.get(id_number=user_id)
    except User.DoesNotExist:
        raise Http404("User not found")
    
    data = {
        'id': user.id,
        'first_name': user.first_name,
        'middle_name':user.middle_name,
        'last_name': user.last_name,
        'contact_number':user.contact_number,
        'email': user.email,
        'department':user.department
    }
    
    return JsonResponse(data)