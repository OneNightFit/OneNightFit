from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .models import Profile


def _role_required(role):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.profile.role != role:
                raise PermissionDenied  # 403
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


buyer_required = _role_required(Profile.Role.BUYER)
seller_required = _role_required(Profile.Role.SELLER)
