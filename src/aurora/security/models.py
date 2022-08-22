from django.contrib.auth.models import Group, User
from django.db import models

from aurora.registration.models import Registration


class RegistrationRole(models.Model):
    registration = models.ForeignKey(Registration, related_name="roles", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        unique_together = (("registration", "user", "role"),)
