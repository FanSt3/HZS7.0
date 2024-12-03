from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from myapp.models import AdminOTP

class EmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(email=username)
            if user.check_password(password):
                return user
        except UserModel.DoesNotExist:
            return None

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

class AdminOTPBackend(ModelBackend):
    def authenticate(self, request, email=None, otp=None):
        User = get_user_model()
        try:
            user = User.objects.get(email=email, is_staff=True)
            otp_obj = user.adminotp_set.filter(
                otp_code=otp,
                is_used=False
            ).latest('created_at')
            
            if otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                return user
            return None
        except (User.DoesNotExist, AdminOTP.DoesNotExist):
            return None

    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None