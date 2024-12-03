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
from .models import AdminOTP, Course, Topic, CourseRating, CourseEnrollment, CourseSection, Lesson, LessonCompletion
from .forms import (
    UserRegisterForm, 
    UserUpdateForm, 
    ProfileUpdateForm, 
    AdminUserCreationForm
)
from django.db.models import Q
import re

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
    # Get topics with course count
    topics = Topic.objects.annotate(
        course_count=Count('course', filter=Q(course__status='published'))
    ).order_by('-course_count')[:6]  # Get top 6 topics

    # Get popular courses
    popular_courses = Course.objects.filter(status='published').annotate(
        avg_rating=Avg('courserating__rating'),
        rating_count=Count('courserating')
    ).order_by('-avg_rating', '-rating_count')[:6]

    context = {
        'topics': topics,
        'popular_courses': popular_courses,
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
    courses = Course.objects.filter(instructor=request.user).annotate(
        avg_rating=Avg('courserating__rating')
    )
    return render(request, 'dashboard/courses.html', {'courses': courses})

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
        'development': 'Development',
        'business': 'Business',
        'finance': 'Finance & Accounting',
        'it': 'IT & Software',
        'design': 'Design',
        'marketing': 'Marketing',
        'lifestyle': 'Lifestyle',
        'photography': 'Photography & Video',
        'health': 'Health & Fitness',
        'music': 'Music',
        'teaching': 'Teaching & Academics'
    }
    
    subcategories = {
        'development': ['Web Development', 'Mobile Development', 'Programming Languages', 'Game Development'],
        'business': ['Entrepreneurship', 'Management', 'Sales', 'Strategy'],
        'finance': ['Accounting', 'Cryptocurrency', 'Finance', 'Investment'],
        'it': ['Network Security', 'Hardware', 'Operating Systems', 'Other IT'],
        'design': ['Web Design', 'Graphic Design', '3D & Animation', 'UI/UX Design'],
        'marketing': ['Digital Marketing', 'Social Media Marketing', 'Branding', 'Marketing Analytics'],
        'lifestyle': ['Arts & Crafts', 'Beauty & Makeup', 'Food & Beverage', 'Pet Care & Training'],
        'photography': ['Digital Photography', 'Video Design', 'Commercial Photography'],
        'health': ['Fitness', 'Sports', 'Mental Health', 'Nutrition'],
        'music': ['Instruments', 'Music Production', 'Vocal', 'Music Theory'],
        'teaching': ['Engineering', 'Math', 'Science', 'Social Science']
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

            messages.success(request, 'Course created successfully!')
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
    course = get_object_or_404(Course, slug=slug, instructor=request.user)
    
    if request.method == 'POST':
        try:
            # Update basic course info
            course.title = request.POST.get('title')
            course.description = request.POST.get('description')
            course.price = request.POST.get('price')
            course.is_free = 'is_free' in request.POST
            course.language = request.POST.get('language')
            course.topic_id = request.POST.get('topic')
            
            if request.FILES.get('image'):
                course.image = request.FILES['image']
            
            course.save()
            
            messages.success(request, 'Course updated successfully!')
            return redirect('admin_courses')
            
        except Exception as e:
            messages.error(request, f'Error updating course: {str(e)}')
    
    context = {
        'course': course,
        'topics': Topic.objects.all(),
        'language_choices': Course.LANGUAGE_CHOICES
    }
    return render(request, 'custom_admin/course_form.html', context)

@user_passes_test(lambda u: u.is_staff)
def admin_course_delete(request, slug):
    if request.method == 'POST':
        try:
            course = get_object_or_404(Course, slug=slug, instructor=request.user)
            course.delete()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

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
            
            messages.success(request, 'Course content updated successfully!')
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
            messages.success(request, 'New admin user has been created successfully!')
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
            messages.success(request, 'User has been removed successfully!')
            return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error'}, status=403)

def course_detail(request, slug):
    course = get_object_or_404(
        Course.objects.select_related('instructor', 'topic')
        .prefetch_related('courserating_set__user__profile')
        .annotate(
            avg_rating=Avg('courserating__rating'),
            rating_count=Count('courserating')
        ),
        slug=slug,
        status='published'
    )
    
    context = {
        'course': course,
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
            messages.error(request, 'Ve ste ocenili ovaj kurs. Možete izmeniti postojeću ocenu.')
            return redirect('course_detail', slug=slug)
            
        if rating:
            CourseRating.objects.create(
                course=course,
                user=request.user,
                rating=rating,
                comment=comment
            )
            messages.success(request, 'Vaša ocena je uspešno sačuvana!')
        
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
    
    messages.success(request, 'Komentar je uspešno obrisan!')
    return redirect('course_detail', slug=course_slug)

def search_courses(request):
    query = request.GET.get('q', '')
    sort = request.GET.get('sort', 'relevance')
    selected_topics = request.GET.getlist('topics')
    is_free = request.GET.get('is_free')

    courses = Course.objects.filter(status='published')

    if query:
        courses = courses.filter(
            Q(title__icontains=query) |
            Q(topic__name__icontains=query) |
            Q(description__icontains=query)
        )

    if selected_topics:
        courses = courses.filter(topic__id__in=selected_topics)

    if is_free:
        courses = courses.filter(is_free=True)

    # Apply sorting
    if sort == 'rating':
        courses = courses.annotate(
            avg_rating=Avg('courserating__rating'),
            rating_count=Count('courserating')
        ).order_by('-avg_rating', '-rating_count')
    elif sort == 'newest':
        courses = courses.order_by('-created_at')
    else:  # relevance - default
        courses = courses.annotate(
            search_rank=Count('courserating')
        ).order_by('-search_rank')

    # Prefetch related data
    courses = courses.select_related('topic', 'instructor').annotate(
        avg_rating=Avg('courserating__rating'),
        rating_count=Count('courserating')
    )

    context = {
        'courses': courses,
        'query': query,
        'sort': sort,
        'selected_topics': selected_topics,
        'is_free': is_free,
        'topics': Topic.objects.all()
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
            messages.success(request, 'Uspešno ste upisali kurs!')
        
        return redirect('course_content', slug=slug)
    return HttpResponseBadRequest()

@login_required
def course_content(request, slug):
    course = get_object_or_404(Course, slug=slug)
    sections = course.coursesection_set.prefetch_related(
        'lesson_set__videos'
    ).all()
    
    completed_lessons = LessonCompletion.objects.filter(
        user=request.user
    ).values_list('lesson_id', flat=True)
    
    # Calculate total lessons
    total_lessons = sum(section.lesson_set.count() for section in sections)
    
    # Calculate progress
    if total_lessons > 0:
        progress = (len(completed_lessons) / total_lessons) * 100
    else:
        progress = 0
        
    context = {
        'course': course,
        'sections': sections,
        'completed_lessons': completed_lessons,
        'total_lessons': total_lessons,
        'progress': progress
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