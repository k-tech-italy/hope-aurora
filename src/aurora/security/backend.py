from django.contrib.auth.backends import ModelBackend

from aurora.registration.models import Registration
from aurora.security.models import RegistrationRole


class SmartBackend(ModelBackend):
    def has_perm(self, user_obj, perm, obj=None):
        if obj and isinstance(obj, Registration):
            return RegistrationRole.objects.filter(user=user_obj, role__permissions__codename=perm).exists()
        return user_obj.is_active and super().has_perm(user_obj, perm, obj=obj)
