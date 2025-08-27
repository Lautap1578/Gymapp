from django.conf import settings


def cdn(request):
    """Expose CDN related settings to templates."""
    return {
        'USE_CDN': getattr(settings, 'USE_CDN', True),
        'CDN_INTEGRITY': getattr(settings, 'CDN_INTEGRITY', {}),
    }
