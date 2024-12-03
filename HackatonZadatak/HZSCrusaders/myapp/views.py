from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import authenticate, login, logout
import random
import string
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from django.contrib.auth.models import User
from .models import AdminOTP

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vaš nalog je uspešno kreiran!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        if 'profile_image' in request.FILES:
            # Obrada promene profilne slike
            p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
            if p_form.is_valid():
                p_form.save()
                messages.success(request, 'Profilna slika je uspešno ažurirana!')
                return redirect('profile')
        else:
            # Obrada promene ostalih podataka
            u_form = UserUpdateForm(request.POST, instance=request.user)
            p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
            
            if u_form.is_valid() and p_form.is_valid():
                u_form.save()
                p_form.save()
                messages.success(request, 'Vaš profil je uspešno ažuriran!')
                return redirect('profile')
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    return render(request, 'profile.html', context)

def home(request):
    return render(request, 'index.html')

def about(request):
    return render(request, 'about.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Dobrodošli nazad, {user.first_name}!')
            return redirect('home')
        else:
            messages.error(request, 'Pogrešan email ili šifra.')
            return render(request, 'login.html')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    messages.success(request, 'Uspešno ste se odjavili!')
    return redirect('home')

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def is_admin(user):
    return user.is_staff

def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        try:
            if email not in settings.ADMIN_EMAILS:
                messages.error(request, 'Niste ovlašćeni za pristup admin panelu.')
                return redirect('home')
                
            user = User.objects.get(email=email, is_staff=True)
            otp = generate_otp()
            AdminOTP.objects.create(user=user, otp_code=otp)
            
            # Send OTP via email
            send_mail(
                'Admin Login OTP',
                f'Vaš OTP kod za admin prijavu je: {otp}',
                settings.EMAIL_HOST_USER,
                [email],
                fail_silently=False,
            )
            
            request.session['admin_email'] = email
            messages.success(request, 'OTP kod je poslat na vašu email adresu.')
            return redirect('admin_verify_otp')
        except User.DoesNotExist:
            messages.error(request, 'Korisnik sa ovom email adresom nije pronađen ili nema admin privilegije.')
    
    return render(request, 'custom_admin/login.html')

def admin_verify_otp(request):
    email = request.session.get('admin_email')
    if not email:
        return redirect('admin_login')
    
    if request.method == 'POST':
        otp = request.POST.get('otp')
        try:
            user = User.objects.get(email=email, is_staff=True)
            otp_obj = AdminOTP.objects.filter(
                user=user,
                otp_code=otp,
                is_used=False
            ).latest('created_at')
            
            # Dodajemo debug ispis
            print(f"OTP from form: {otp}")
            print(f"OTP from DB: {otp_obj.otp_code}")
            print(f"Is valid: {otp_obj.is_valid()}")
            
            if otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                del request.session['admin_email']
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'OTP je istekao ili je već iskorišćen.')
        except (User.DoesNotExist, AdminOTP.DoesNotExist):
            messages.error(request, 'Nevažeći OTP kod.')
    
    return render(request, 'custom_admin/verify_otp.html')

@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users = User.objects.count()
    new_users = User.objects.filter(
        date_joined__date=timezone.now().date()
    ).count()
    
    context = {
        'total_users': total_users,
        'new_users': new_users
    }
    return render(request, 'custom_admin/dashboard.html', context)

def admin_logout(request):
    logout(request)
    messages.success(request, 'Successfully logged out from admin panel.')
    return redirect('admin_login')