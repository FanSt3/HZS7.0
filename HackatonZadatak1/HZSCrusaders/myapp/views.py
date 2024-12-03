from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import AdminOTP
from .config import ADMIN_EMAILS, EMAIL_CONFIG
import random
import string
from django.core.mail import send_mail
from django.http import JsonResponse

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

def is_admin_email(email):
    return email in ADMIN_EMAILS

def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = request.POST.get('otp')

        if not is_admin_email(email):
            messages.error(request, 'Unauthorized access')
            return redirect('admin_login')

        if 'send_otp' in request.POST:
            new_otp = generate_otp()
            AdminOTP.objects.create(email=email, otp=new_otp)
            
            send_mail(
                'Admin Panel OTP',
                f'Your OTP is: {new_otp}. Valid for 5 minutes.',
                EMAIL_CONFIG['EMAIL_HOST_USER'],
                [email],
                fail_silently=False,
            )
            messages.success(request, 'OTP sent to your email')
            return render(request, 'admin/login.html', {'email': email, 'show_otp': True})

        if otp:
            admin_otp = AdminOTP.objects.filter(
                email=email,
                otp=otp,
                is_used=False
            ).order_by('-created_at').first()

            if admin_otp and admin_otp.is_valid:
                admin_otp.is_used = True
                admin_otp.save()
                request.session['admin_authenticated'] = True
                request.session['admin_email'] = email
                return redirect('admin_dashboard')
            
            messages.error(request, 'Invalid or expired OTP')

    return render(request, 'admin/login.html')

def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.session.get('admin_authenticated'):
            return redirect('admin_login')
        return view_func(request, *args, **kwargs)
    return wrapper

@admin_required
def admin_dashboard(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin/dashboard.html', {'users': users})

@admin_required
def admin_logout(request):
    request.session.pop('admin_authenticated', None)
    request.session.pop('admin_email', None)
    messages.success(request, 'Successfully logged out')
    return redirect('admin_login')

@admin_required
def delete_user(request, user_id):
    if request.method == 'POST':
        try:
            user = User.objects.get(id=user_id)
            if user.email not in ADMIN_EMAILS:  # Sprečavamo brisanje admin korisnika
                user.delete()
                return JsonResponse({'status': 'success'})
            return JsonResponse({'status': 'error', 'message': 'Ne možete obrisati administratora'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Korisnik nije pronađen'})
    return JsonResponse({'status': 'error', 'message': 'Neispravan zahtev'})