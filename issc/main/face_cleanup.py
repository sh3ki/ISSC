"""Cleanup for account-linked face data without removing recognition history."""

import sys

from .models import FacesEmbeddings


def _remove_from_matcher(matcher, id_number):
    if matcher is not None and hasattr(matcher, 'embeddings'):
        matcher.embeddings.pop(id_number, None)


def clear_account_face_caches(id_number):
    """Remove one account from recognition caches in the current process."""
    loaded_modules = sys.modules

    for module_name in (
        'main.views.video_feed_view',
        'main.views.lightning_camera_system',
        'main.views.simple_lightning_camera',
        'main.views.ultra_fast_camera',
    ):
        module = loaded_modules.get(module_name)
        if module is not None:
            _remove_from_matcher(getattr(module, 'matcher', None), id_number)
            manager = getattr(module, 'lightning_camera_manager', None)
            manager = manager or getattr(module, 'simple_lightning_manager', None)
            manager = manager or getattr(module, 'ultra_fast_manager', None)
            if manager is not None:
                _remove_from_matcher(getattr(manager, 'face_matcher', None), id_number)

    module = loaded_modules.get('main.views.enhanced_video_feed')
    if module is not None:
        manager = getattr(module, 'enhanced_camera_manager', None)
        _remove_from_matcher(getattr(manager, 'matcher', None), id_number)

    module = loaded_modules.get('main.views.live_feed_simple')
    if module is not None:
        cache = getattr(module, 'face_embeddings_cache', None)
        lock = getattr(module, 'face_embeddings_lock', None)
        if isinstance(cache, dict):
            if lock is not None:
                with lock:
                    cache.pop(id_number, None)
            else:
                cache.pop(id_number, None)

    module = loaded_modules.get('main.computer_vision.face_recognition_engine')
    if module is not None:
        engine = getattr(module, 'face_engine', None)
        for cache_name in (
            'embeddings_cache',
            'normalized_embeddings_cache',
            'user_info_cache',
        ):
            cache = getattr(engine, cache_name, None)
            if isinstance(cache, dict):
                cache.pop(id_number, None)


def remove_account_face_data(account):
    """Remove enrolled face data and clear loaded recognition caches.

    FaceLogs are intentionally not touched; their foreign key is SET_NULL so
    they remain available for audit after the account is deleted.
    """
    # Explicit cleanup keeps this behavior clear even though the model FK is
    # also configured with CASCADE.
    FacesEmbeddings.objects.filter(id_number=account).delete()
    clear_account_face_caches(account.id_number)
