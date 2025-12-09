from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
from datetime import datetime


# Create your models here.

class AccountRegistration(AbstractUser):
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    id_number = models.CharField(max_length=50, unique=True)
    contact_number = models.CharField(max_length=15)
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    department = models.CharField(max_length=100)
    PRIVILEGE_CHOICES = [
        ('student', 'Student'),
        ('faculty', 'Faculty'),
        ('admin', 'Admin'),
    ]
    privilege = models.CharField(max_length=10, choices=PRIVILEGE_CHOICES)
    STATUS_CHOICES = [
        ('allowed', 'Allowed'),
        ('restricted', 'Restricted'),
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "Account Registration"
        verbose_name_plural = "Account Registrations"


class VehicleRegistration(models.Model):
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30)
    id_number = models.CharField(max_length=100, unique=True)
    contact_number = models.CharField(max_length=15)
    email_address = models.EmailField(unique=True)
    role = models.CharField(max_length=20)
    vehicle_type = models.CharField(max_length=50)
    color = models.CharField(max_length=30)
    model = models.CharField(max_length=50)
    plate_number = models.CharField(max_length=20, unique=True)
    sticker_number = models.CharField(max_length=20, unique=True)
    guardian_name = models.CharField(max_length=100)
    guardian_number = models.CharField(max_length=15)
    image = models.ImageField(upload_to='images/')
    drivers_license = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=20, choices=[
        ('allowed', 'Allowed'),
        ('restricted', 'Restricted')
    ])
    qr_code = models.ImageField(upload_to='images/')
    date_joined = models.DateTimeField(auto_now_add=True)

    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by =  models.CharField(max_length=100)
    is_archived = models.BooleanField()


    def __str__(self):
        return self.id_number

    class Meta:
        verbose_name = "Vehicle Registration"
        verbose_name_plural = "Vehicle Registrations"


class IncidentReport(models.Model):
    first_name = models.CharField(max_length=30)
    middle_name = models.CharField(max_length=30, null=True, blank=True)
    last_name = models.CharField(max_length=30)
    contact_number = models.CharField(max_length=15)
    id_number = models.CharField(max_length=100)
    subject = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    date_joined = models.DateTimeField(auto_now_add=True)
    incident = models.TextField()
    request_for_action = models.TextField()
    people_involved = models.TextField(null=True, blank=True)
    faculty_involved = models.ManyToManyField(AccountRegistration, blank=True, related_name='incident_reports')
    reported_by = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=15)
    file = models.FileField(upload_to='files/')
    status = models.CharField(max_length=20, choices=[
        ('open', 'Open'),
        ('closed', 'Closed'),
        ('pending', 'Pending')
    ])
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)

    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by =  models.CharField(max_length=100)

    is_archived = models.BooleanField()
    invalidation_reason = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.subject}"


class IncidentUpdate(models.Model):
    """A record of an update/action taken on an IncidentReport.

    Stores an update reason, optional attachment, who created the update,
    and whether the update closed the case.
    """
    incident = models.ForeignKey('IncidentReport', related_name='updates', on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    file = models.FileField(upload_to='files/incident_updates/', null=True, blank=True)
    created_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    close_case = models.BooleanField(default=False)

    def __str__(self):
        return f"Update for Incident {self.incident.id} at {self.created_at} by {self.created_by}"

    class Meta:
        verbose_name = "Incident Update"
        verbose_name_plural = "Incident Updates"
        ordering = ['-created_at']


class FacesEmbeddings(models.Model):
    face_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_number = models.ForeignKey(AccountRegistration, to_field="id_number", on_delete=models.CASCADE)
    front_embedding = models.JSONField(default=dict)
    left_embedding = models.JSONField(default=dict)
    right_embedding = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Face entry for {self.id_number.id_number} at {self.created_at}"

    class Meta:
        verbose_name = "Face Embedding"
        verbose_name_plural = "Faces Embeddings"

class FaceLogs(models.Model):
    id_number = models.ForeignKey(AccountRegistration, to_field="id_number", on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date = models.DateField(auto_now_add=True)
    time = models.TimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f" Face Log at : {self.id_number.id_number} at {self.created_at}"

    class Meta:
        verbose_name = "Face Logs"
        verbose_name_plural = "Face Logs"

class VehicleEntry(models.Model):
    entry_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    vehicle = models.ForeignKey('VehicleRegistration', on_delete=models.SET_NULL, null=True, blank=True, related_name='entries')
    
    is_registered = models.BooleanField(default=True)
    
    entry_timestamp = models.DateTimeField(auto_now_add=True)
    exit_timestamp = models.DateTimeField(null=True, blank=True)
    
    entry_gate = models.CharField(max_length=100)
    exit_gate = models.CharField(max_length=100, null=True, blank=True)
    
    qr_code_scanned = models.BooleanField(default=False)
    
    is_exited = models.BooleanField(default=False)
    
    last_updated = models.DateTimeField(auto_now=True)
    last_updated_by = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        """Automatically determine if the vehicle is registered or not."""
        if self.vehicle:
            self.is_registered = True  # Vehicle exists in VehicleRegistration
        else:
            self.is_registered = False  # Unregistered vehicle
        super().save(*args, **kwargs)

    def __str__(self):
        reg_status = "Registered" if self.is_registered else "Unregistered"
        return f"{reg_status} Vehicle Entry for {self.vehicle.plate_number if self.vehicle else 'Unknown'} at {self.entry_timestamp}"

    class Meta:
        verbose_name = "Vehicle Entry"
        verbose_name_plural = "Vehicle Entries"


class UnauthorizedFaceDetection(models.Model):
    detection_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image_path = models.CharField(max_length=500)  # Path to saved image
    camera_box_id = models.IntegerField()  # Which camera box detected this
    detection_timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)  # Optional notes
    
    def __str__(self):
        return f"Unauthorized detection at {self.detection_timestamp} (Camera {self.camera_box_id})"
    
    class Meta:
        verbose_name = "Unauthorized Face Detection"
        verbose_name_plural = "Unauthorized Face Detections"
        ordering = ['-detection_timestamp']  # Most recent first
