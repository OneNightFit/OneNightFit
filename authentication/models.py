from django.conf import settings
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Profile(models.Model):
    class Role(models.TextChoices):
        BUYER = "buyer", "Buyer"
        SELLER = "seller", "Seller"

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def is_buyer(self):
        return self.role == self.Role.BUYER

    @property
    def is_seller(self):
        return self.role == self.Role.SELLER

class ActivityHistory(models.Model):
    class Action(models.TextChoices):
        REGISTER = "register", "Account created"
        LOGIN = "login", "Logged in"
        LOGOUT = "logout", "Logged out"
        EDIT_PROFILE = "edit_profile", "Profile updated"
        CHANGE_PASSWORD = "change_password", "Password changed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activities"
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    description = models.CharField(max_length=200, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "Activity histories"

    def __str__(self):
        return f"{self.user.username} - {self.get_action_display()}"

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs): 
    if created:
        Profile.objects.create(user=instance)
