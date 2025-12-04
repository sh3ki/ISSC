from django.contrib import admin
from .models import AccountRegistration, VehicleRegistration, IncidentReport, FacesEmbeddings, VehicleEntry, FaceLogs, UnauthorizedFaceDetection, IncidentUpdate
# Register your models here.
admin.site.register(AccountRegistration)
admin.site.register(VehicleRegistration)
admin.site.register(IncidentReport)
admin.site.register(FacesEmbeddings)
admin.site.register(VehicleEntry)
admin.site.register(FaceLogs)
admin.site.register(UnauthorizedFaceDetection)
admin.site.register(IncidentUpdate)
