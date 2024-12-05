from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Avg, Count
from django.db.models.functions import Coalesce
from django.utils.text import slugify
from django.http import JsonResponse, HttpResponseBadRequest
from datetime import timedelta
import random
import string
from django.core.mail import send_mail
from django.core import serializers
import json
from django.core.serializers.json import DjangoJSONEncoder
from .models import AdminOTP, Course, Topic, CourseRating, CourseEnrollment, CourseSection, Lesson, LessonCompletion, CourseReview, Profile
from .forms import (
    UserRegisterForm, 
    UserUpdateForm, 
    ProfileUpdateForm, 
    AdminUserCreationForm
)
from django.db.models import Q
import re
from django.contrib.auth.forms import UserChangeForm
from django.db import connection
from django.views.decorators.http import require_POST

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            Profile.objects.get_or_create(user=user)
            messages.success(request, 'Vaš nalog je uspešno kreiran!')
            return redirect('login')
    else:
        form = UserRegisterForm()
    return render(request, 'register.html', {'form': form})

@login_required
def profile(request):
    if request.method == 'POST':
        if 'avatar' in request.FILES:
            profile = request.user.profile
            profile.avatar = request.FILES['avatar']
            profile.save()
            messages.success(request, 'Profilna slika je uspešno ažurirana!')
            return redirect('profile')
        else:
            # Handle other profile updates
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            email = request.POST.get('email')
            
            user = request.user
            user.first_name = first_name
            user.last_name = last_name
            user.email = email
            user.save()
            
            messages.success(request, 'Profil je uspešno ažuriran!')
            return redirect('profile')
            
    return render(request, 'profile.html')

def home(request):
    popular_courses = Course.objects.filter(
        status='published'
    ).select_related('instructor', 'topic').annotate(
        rating_average=Avg('reviews__rating'),
        rating_count=Count('reviews')
    ).order_by('-rating_count')[:6]

    # Get top 8 topics by course count
    topics = Topic.objects.annotate(
        course_count=Count('course', filter=Q(course__status='published'))
    ).order_by('-course_count')[:8]

    context = {
        'popular_courses': popular_courses,
        'topics': topics,
    }
    return render(request, 'index.html', context)

def about(request):
    return render(request, 'about.html')

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, 'Pogrešan email ili šifra.')
            return render(request, 'login.html')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
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
            
            if otp_obj.is_valid():
                otp_obj.is_used = True
                otp_obj.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                del request.session['admin_email']
                messages.success(request, 'Uspešno ste se prijavili!')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'OTP je istekao ili je već iskorišćen.')
        except (User.DoesNotExist, AdminOTP.DoesNotExist):
            messages.error(request, 'Nevažeći OTP kod.')
    
    return render(request, 'custom_admin/verify_otp.html')

@user_passes_test(is_admin)
def admin_dashboard(request):
    total_users = User.objects.count()
    total_courses = Course.objects.count()
    recent_users = User.objects.order_by('-date_joined')[:5]
    recent_courses = Course.objects.order_by('-created_at')[:5]
    
    context = {
        'total_users': total_users,
        'total_courses': total_courses,
        'recent_users': recent_users,
        'recent_courses': recent_courses,
    }
    return render(request, 'custom_admin/dashboard.html', context)

@user_passes_test(is_admin)
def admin_users(request):
    users = User.objects.all().order_by('-date_joined')
    return render(request, 'dashboard/users.html', {'users': users})

@user_passes_test(lambda u: u.is_staff)
def admin_courses(request):
    courses = Course.objects.filter(
        instructor=request.user
    ).select_related('topic').annotate(
        rating_average=Avg('reviews__rating'),
        rating_count=Count('reviews'),
        student_count=Count('enrolled_students'),
        section_count=Count('coursesection')
    ).order_by('-created_at')

    context = {
        'courses': courses,
    }
    return render(request, 'dashboard/courses.html', context)

def admin_logout(request):
    logout(request)
    messages.success(request, 'Successfully logged out from admin panel.')
    return redirect('admin_login')

def topic_detail(request, slug):
    topic = get_object_or_404(Topic, slug=slug)
    courses = Course.objects.filter(topic=topic).annotate(
        avg_rating=Avg('courserating__rating'),
        rating_count=Count('courserating')
    )
    
    context = {
        'topic': topic,
        'courses': courses,
    }
    return render(request, 'topic_detail.html', context)

@user_passes_test(is_admin)
def admin_course_create(request):
    # Define categories at the start of the view
    categories = {
        'development': 'Razvoj softvera',
        'business': 'Biznis',
        'finance': 'Finansije & Računovodstvo',
        'it': 'Infomracione tehnologije',
        'design': 'Dizajn',
        'marketing': 'Marketing',
        'lifestyle': 'Lifestyle',
        'photography': 'Fotografija & Video',
        'health': 'Zdravlje & Sport',
        'music': 'Muzika',
        'teaching': 'Pedagogija & Nauka'
    }
    
    subcategories = {
        'development': ['Razvoj web aplikacija', 'Razvoj mobilnih aplikacija', 'Programski jezici', 'Razvoj igara'],
        'business': ['Preduzetništvo', 'Menadžment', 'Prodaja'],
        'finance': ['Računovodstvo', 'Kripto Valute', 'Finansije', 'Investiranje'],
        'it': ['Mrežna bezbednost', 'Hardver', 'Operativni sistemi', 'Ostalo'],
        'design': ['Web Dizajn', 'Grafički dizajn', '3D & Animacije', 'UI/UX Dizajn'],
        'marketing': ['Digitalni Marketing', 'Marketing za društvene mreže', 'Brendiranje', 'Marketinška analitika'],
        'lifestyle': ['Kreativne veštine', 'Lapota & šminka', 'Kulinarstvo', 'Dresiranje i briga o kućnim ljubimcima'],
        'photography': ['Digitalna Fotografija', 'Video Montaža', 'Komercijalna Fotografija'],
        'health': ['Fitnes', 'Sport', 'Mentalno zdravlje', 'Nutricionizam'],
        'music': ['Instrumenti', 'Muzička produkcija', 'Pevanje', 'Teorija muzike'],
        'teaching': ['Inženjerstvo', 'Matematika', 'Prirodne nauke', 'Društvene nauke']
    }

    if request.method == 'POST':
        try:
            # Get the main category and subcategory
            main_category = request.POST.get('main-category')
            subcategory = request.POST.get('topic')

            # Create or get the topic
            topic, created = Topic.objects.get_or_create(
                name=subcategory,
                defaults={'category': main_category}
            )

            # Create course
            course = Course.objects.create(
                title=request.POST.get('title'),
                description=request.POST.get('description'),
                topic=topic,
                language=request.POST.get('language'),
                price=request.POST.get('price', 0),
                instructor=request.user,
                status='published'
            )
            
            if 'image' in request.FILES:
                course.image = request.FILES['image']
                course.save()

            # Process sections and lessons
            section_titles = request.POST.getlist('section_title[]')
            
            for i, title in enumerate(section_titles, 1):
                if title:
                    section = CourseSection.objects.create(
                        course=course,
                        title=title,
                        order=i
                    )
                    
                    # Get lessons for this section
                    lesson_titles = request.POST.getlist(f'lesson_title[{i-1}][]')
                    lesson_contents = request.POST.getlist(f'lesson_content[{i-1}][]')
                    lesson_videos = request.POST.getlist(f'lesson_video[{i-1}][]')
                    
                    for j, (ltitle, content, video) in enumerate(
                        zip(lesson_titles, lesson_contents, lesson_videos), 1):
                        if ltitle:
                            Lesson.objects.create(
                                section=section,
                                title=ltitle,
                                content=content,
                                video_url=video,
                                order=j
                            )

            return redirect('admin_dashboard')
            
        except Exception as e:
            messages.error(request, f'Error creating course: {str(e)}')
            print(f"Error details: {str(e)}")  # Add this for debugging
    
    context = {
        'main_categories': categories,
        'subcategories': subcategories,
        'language_choices': Course.LANGUAGE_CHOICES
    }
    return render(request, 'custom_admin/course_form.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_course_edit(request, slug):
    # Define categories
    categories = {
        'development': 'Razvoj softvera',
        'business': 'Biznis',
        'finance': 'Finansije & Računovodstvo',
        'it': 'Infomracione tehnologije',
        'design': 'Dizajn',
        'marketing': 'Marketing',
        'lifestyle': 'Lifestyle',
        'photography': 'Fotografija & Video',
        'health': 'Zdravlje & Sport',
        'music': 'Muzika',
        'teaching': 'Pedagogija & Nauka'
    }
    
    subcategories = {
        'development': ['Razvoj web aplikacija', 'Razvoj mobilnih aplikacija', 'Programski jezici', 'Razvoj igara'],
        'business': ['Preduzetništvo', 'Menadžment', 'Prodaja'],
        'finance': ['Računovodstvo', 'Kripto Valute', 'Finansije', 'Investiranje'],
        'it': ['Mrežna bezbednost', 'Hardver', 'Operativni sistemi', 'Ostalo'],
        'design': ['Web Dizajn', 'Grafički dizajn', '3D & Animacije', 'UI/UX Dizajn'],
        'marketing': ['Digitalni Marketing', 'Marketing za društvene mreže', 'Brendiranje', 'Marketinška analitika'],
        'lifestyle': ['Kreativne veštine', 'Lapota & šminka', 'Kulinarstvo', 'Dresiranje i briga o kućnim ljubimcima'],
        'photography': ['Digitalna Fotografija', 'Video Montaža', 'Komercijalna Fotografija'],
        'health': ['Fitnes', 'Sport', 'Mentalno zdravlje', 'Nutricionizam'],
        'music': ['Instrumenti', 'Muzička produkcija', 'Pevanje', 'Teorija muzike'],
        'teaching': ['Inženjerstvo', 'Matematika', 'Prirodne nauke', 'Društvene nauke']
    }

    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    
    if request.method == 'POST':
        try:
            # Update basic course info
            course.title = request.POST.get('title')
            course.description = request.POST.get('description')
            course.price = request.POST.get('price')
            course.language = request.POST.get('language')
            
            # Only update category/topic if they were changed
            main_category = request.POST.get('main-category')
            subcategory = request.POST.get('topic')
            
            if main_category and subcategory:
                topic, created = Topic.objects.get_or_create(
                    name=subcategory,
                    defaults={'category': main_category}
                )
                course.topic = topic
            
            if request.FILES.get('image'):
                course.image = request.FILES['image']
            
            course.save()
            

            return redirect('admin_courses')
            
        except Exception as e:
            messages.error(request, f'Greška pri ažuriranju kursa: {str(e)}')
    
    # Add existing values to context
    context = {
        'course': course,
        'main_categories': categories,
        'subcategories': subcategories,
        'language_choices': Course.LANGUAGE_CHOICES
    }
    return render(request, 'custom_admin/course_form.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_course_delete(request, slug):
    if request.method == 'POST':
        try:
            # First get the course and verify ownership
            course = Course.objects.get(slug=slug, instructor=request.user)
            
            # Delete related sections and lessons first
            CourseSection.objects.filter(course=course).delete()
            
            # Then delete the course
            course.delete()
            
            return JsonResponse({'status': 'success'})
        except Course.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Kurs nije pronađen'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method'
    }, status=405)

@user_passes_test(lambda u: u.is_staff)
def admin_course_content(request, slug):
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    
    if request.method == 'POST':
        try:
            # Get all section titles
            section_titles = request.POST.getlist('section_title[]')
            
            # Delete existing sections and lessons
            CourseSection.objects.filter(course=course).delete()
            
            # Create new sections and lessons
            for i, title in enumerate(section_titles, 1):
                if title:
                    section = CourseSection.objects.create(
                        course=course,
                        title=title,
                        order=i
                    )
                    
                    # Get lessons for this section
                    lesson_titles = request.POST.getlist(f'lesson_title[{i-1}][]')
                    lesson_contents = request.POST.getlist(f'lesson_content[{i-1}][]')
                    lesson_videos = request.POST.getlist(f'lesson_video[{i-1}][]')
                    
                    for j, (ltitle, content, video) in enumerate(
                        zip(lesson_titles, lesson_contents, lesson_videos), 1):
                        if ltitle:
                            Lesson.objects.create(
                                section=section,
                                title=ltitle,
                                content=content,
                                video_url=video,
                                order=j
                            )
            

            return redirect('admin_courses')
            
        except Exception as e:
            messages.error(request, f'Error updating course content: {str(e)}')
    
    sections = CourseSection.objects.filter(course=course).prefetch_related('lesson_set')
    context = {
        'course': course,
        'sections': sections
    }
    return render(request, 'custom_admin/course_content.html', context)

@user_passes_test(is_admin)
def admin_add_user(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('admin_dashboard')
    else:
        form = AdminUserCreationForm()
    
    return render(request, 'custom_admin/add_user.html', {'form': form})

@user_passes_test(is_admin)
def admin_remove_user(request, user_id):
    if request.method == 'POST':
        user = get_object_or_404(User, id=user_id)
        if not user.is_staff and user != request.user:  # Can't remove admins or yourself
            user.delete()
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=403)

def course_detail(request, slug):
    course = get_object_or_404(Course.objects.select_related(
        'instructor', 
        'topic'
    ).prefetch_related(
        'reviews',
        'reviews__user',
        'reviews__user__profile'
    ), slug=slug)
    
    user_review = None
    if request.user.is_authenticated:
        user_review = course.reviews.filter(user=request.user).first()
    
    context = {
        'course': course,
        'user_review': user_review,
    }
    return render(request, 'course_detail.html', context)

@login_required
def submit_course_rating(request, slug):
    if request.method == 'POST':
        course = get_object_or_404(Course, slug=slug)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Check if user already has a review
        existing_rating = CourseRating.objects.filter(course=course, user=request.user).first()
        
        if existing_rating:
            messages.error(request, 'Već ste ocenili ovaj kurs. Možete izmeniti postojeću ocenu.')
            return redirect('course_detail', slug=slug)
            
        if rating:
            CourseRating.objects.create(
                course=course,
                user=request.user,
                rating=rating,
                comment=comment
            )
        
        return redirect('course_detail', slug=slug)
    return HttpResponseBadRequest()

def course_list(request):
    courses = Course.objects.filter(
        status='published'
    ).select_related('instructor', 'topic').annotate(
        avg_rating=Avg('courserating__rating'),
        rating_count=Count('courserating')
    ).order_by('-created_at')
    
    context = {
        'courses': courses,
    }
    return render(request, 'course_list.html', context)

@login_required
def delete_course_rating(request, rating_id):
    rating = get_object_or_404(CourseRating, id=rating_id)
    
    if not (request.user.is_staff or rating.user == request.user):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
    
    course_slug = rating.course.slug
    rating.delete()
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'success'})
    

    return redirect('course_detail', slug=course_slug)

def search_courses(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'relevance')
    is_free = request.GET.get('is_free', False)
    topic_ids = request.GET.getlist('topics')
    
    # Start with all courses and annotate with rating info
    courses = Course.objects.annotate(
        rating_average=Avg('reviews__rating'),
        rating_count=Count('reviews')
    )
    
    # Apply topic filter if any topics are selected
    if topic_ids:
        courses = courses.filter(topic_id__in=topic_ids)
    
    # Apply text search if query exists
    if query:
        courses = courses.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(topic__name__icontains=query)
        )
    
    # Apply free courses filter
    if is_free:
        courses = courses.filter(is_free=True)
    
    # Apply sorting
    if sort == 'rating':
        courses = courses.order_by('-rating_average', '-created_at')
    elif sort == 'newest':
        courses = courses.order_by('-created_at')
    
    context = {
        'courses': courses,
        'query': query,
        'sort': sort,
        'is_free': is_free,
        'selected_topics': topic_ids,
    }
    
    return render(request, 'search_results.html', context)

@login_required
def enroll_course(request, slug):
    if request.method == 'POST':
        course = get_object_or_404(Course, slug=slug)
        
        # Check if already enrolled
        if not CourseEnrollment.objects.filter(user=request.user, course=course).exists():
            CourseEnrollment.objects.create(
                user=request.user,
                course=course
            )
        
        return redirect('course_content', slug=slug)
    return HttpResponseBadRequest()

@login_required
def course_content(request, slug):
    course = get_object_or_404(Course, slug=slug)
    
    if not CourseEnrollment.objects.filter(user=request.user, course=course).exists():
        messages.error(request, 'Morate biti upisani da biste pristupili sadržaju kursa.')
        return redirect('course_detail', slug=slug)
    
    sections = CourseSection.objects.filter(course=course).prefetch_related('lesson_set')
    completed_lessons = LessonCompletion.objects.filter(
        user=request.user,
        lesson__section__course=course
    ).values_list('lesson_id', flat=True)
    
    # Prepare lesson data with video URLs
    for section in sections:
        for lesson in section.lesson_set.all():
            if lesson.video_url:
                # Convert YouTube URLs to embed format if needed
                if 'youtube.com/watch?v=' in lesson.video_url:
                    video_id = lesson.video_url.split('v=')[1].split('&')[0]
                    lesson.video_url = f'https://www.youtube.com/embed/{video_id}'
                elif 'youtu.be/' in lesson.video_url:
                    video_id = lesson.video_url.split('/')[-1]
                    lesson.video_url = f'https://www.youtube.com/embed/{video_id}'
    
    context = {
        'course': course,
        'sections': sections,
        'completed_lessons': completed_lessons,
        'progress': course.get_progress(request.user)
    }
    return render(request, 'course_content.html', context)

@login_required
def complete_lesson(request, lesson_id):
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # Verify user is enrolled in the course
        if not CourseEnrollment.objects.filter(
            user=request.user, 
            course=lesson.section.course
        ).exists():
            return JsonResponse({'status': 'error', 'message': 'Not enrolled'}, status=403)
        
        # Mark lesson as complete
        LessonCompletion.objects.get_or_create(
            user=request.user,
            lesson=lesson
        )
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=405)

@login_required
def add_review(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        # Check if user already reviewed
        existing_review = CourseReview.objects.filter(course=course, user=request.user).first()
        if existing_review:
            return redirect('course_detail', slug=slug)
        
        CourseReview.objects.create(
            course=course,
            user=request.user,
            rating=rating,
            comment=comment
        )
        return redirect('course_detail', slug=slug)
    return HttpResponseBadRequest()

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(CourseReview, id=review_id)
    if request.user == review.user or request.user == review.course.instructor:
        review.delete()
        messages.success(request, 'Recenzija je uspešno obrisana!')
    else:
        messages.error(request, 'Nemate dozvolu za brisanje ove recenzije.')
    return redirect('course_detail', slug=review.course.slug)

@user_passes_test(is_admin)
def admin_user_edit(request, user_id):
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_users')
    else:
        form = UserChangeForm(instance=user)
    
    return render(request, 'dashboard/user_edit.html', {
        'form': form,
        'edit_user': user
    })

def get_topics(request):
    # Get all topics and convert to list of dicts
    topics = Topic.objects.values('id', 'name', 'category')
    
    # Format the response
    topics_list = list(topics)
    
    # Return JSON response
    return JsonResponse(topics_list, safe=False)