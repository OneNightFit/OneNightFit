from .models import ActivityHistory


def get_client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_activity(request, user, action, description=""):
    ActivityHistory.objects.create(
        user=user,
        action=action,
        description=description,
        ip_address=get_client_ip(request),
    )
