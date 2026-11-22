from django.db.models.signals import post_delete
from django.dispatch import receiver

from .face_cleanup import clear_account_face_caches
from .models import AccountRegistration


@receiver(post_delete, sender=AccountRegistration)
def clear_deleted_account_face_cache(sender, instance, **kwargs):
    """Cover account deletions made outside the normal account views."""
    clear_account_face_caches(instance.id_number)
