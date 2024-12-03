from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegisterForm, UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import authenticate, login, logout

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