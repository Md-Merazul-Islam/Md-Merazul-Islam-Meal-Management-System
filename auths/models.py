from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from datetime import timedelta
now = timezone.now()


class Role(models.TextChoices):
    ADMIN = 'admin', 'Admin'
    USER = 'user', 'User'
    DELIVERY_MAN = 'delivery_man', 'Delivery Man'
    BEKARY = 'bekary', 'Bekary'


class CustomUser(AbstractUser):
    email = models.EmailField(unique=True, db_index=True)
    role = models.CharField(max_length=100, choices=Role.choices,
                            default=Role.USER, null=True, blank=True, db_index=True)
    address = models.CharField(
        max_length=255, null=True, blank=True, db_index=True)
    city = models.CharField(max_length=255, null=True,
                            blank=True, db_index=True)
    postal_code = models.CharField(
        max_length=255, null=True, blank=True, db_index=True)
    phone_number = models.CharField(
        max_length=15, null=True, blank=True, db_index=True)
    photo = models.CharField(max_length=255, blank=True, null=True)
    trial_status = models.BooleanField(default=False, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_created_at = models.DateTimeField(auto_now_add=True)

    def is_otp_expired(self):
        if self.otp_created_at:
            return timezone.now() > self.otp_created_at + timezone.timedelta(minutes=10)
        return True

    def __str__(self):
        return f"Profile of {self.user.email}"

from django.db import models
from django.utils import timezone
from datetime import timedelta

class CommitmentForSixMonths(models.Model):
    user = models.ForeignKey(
        'CustomUser', on_delete=models.CASCADE, related_name='commitments')
    commitment_status = models.BooleanField(default=False)  # False means not committed, True means committed
    committed_once = models.BooleanField(default=False)  # True once user has committed
    commitment_start_date = models.DateField(auto_now_add=True, null=True)
    commitment_end_date = models.DateField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.commitment_start_date is None:
            self.commitment_start_date = timezone.now().date()

        if not self.commitment_end_date:
            self.commitment_end_date = self.commitment_start_date + timedelta(days=30*6)  # 6 months from start

        super().save(*args, **kwargs)

    def is_commitment_active(self):
        """Returns whether the commitment is still active based on the status and expiration date."""
        return self.commitment_status and timezone.now().date() <= self.commitment_end_date

    def reset_commitment(self):
        """Resets commitment status and clears all related information. Admins can use this."""
        self.commitment_status = False
        self.commitment_start_date = None
        self.commitment_end_date = None
        self.save()

    def activate_commitment(self):
        """Activate commitment if not already active and user has not deactivated it manually."""
        if self.committed_once and not self.commitment_status:
            raise ValueError("You cannot reactivate the commitment once it has been deactivated by admin.")
        
        self.commitment_status = True
        self.commitment_start_date = timezone.now().date()
        self.commitment_end_date = self.commitment_start_date + timedelta(days=30*6)  # 6 months from now
        self.committed_once = True  # Mark as committed once
        self.save()

    def deactivate_commitment(self):
        """Deactivate commitment and prevent reactivation by the user."""
        self.commitment_status = False
        self.save()

    @classmethod
    def create_or_check_commitment(cls, user):
        """Check if the user has already committed, if not create a new commitment"""
        commitment, created = cls.objects.get_or_create(user=user)
        if created:  # If the commitment was newly created
            commitment.activate_commitment()
            return "New commitment created"
        else:
            if commitment.is_commitment_active():
                return "Already committed"
            else:
                if commitment.committed_once:
                    return "Commitment deactivated by admin. Cannot reactivate."
                commitment.activate_commitment()
                return "Re-activated commitment"
