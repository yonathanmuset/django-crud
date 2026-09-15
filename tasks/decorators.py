from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role != role:
                return redirect("role_dashboard")
            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator
