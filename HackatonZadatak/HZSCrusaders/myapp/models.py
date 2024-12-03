from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='default.png', upload_to='profile_pics')
    bio = models.TextField(max_length=500, blank=True)

    def __str__(self):
        return f'{self.user.username} Profile'

class AdminOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        now = timezone.now()
        expiry_time = self.created_at + timedelta(minutes=5)
        return now <= expiry_time and not self.is_used

    def __str__(self):
        return f'OTP for {self.user.email}'