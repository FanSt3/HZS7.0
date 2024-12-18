from datetime import timedelta
from django.utils import timezone
from django.db import models
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.http import JsonResponse

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(max_length=500, blank=True)
    is_instructor = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.username} Profile'

class Topic(models.Model):
    CATEGORY_CHOICES = [
        ('development', 'Razvoj softvera'),
        ('business', 'Biznis'),
        ('finance', 'Finansije & Računovodstvo'),
        ('it', 'Infomracione tehnologije'),
        ('design', 'Dizajn'),
        ('marketing', 'Marketing'),
        ('lifestyle', 'Lifestyle'),
        ('photography', 'Fotografija & Video'),
        ('health', 'Zdravlje & Sport'),
        ('music', 'Muzika'),
        ('teaching', 'Teaching & Academics')
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES,
        default='development'
    )
    
    class Meta:
        ordering = ['name']
        unique_together = ['name', 'category']
    
    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

class Course(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'Engleski'),
        ('sr', 'Srpski'),
        ('de', 'Nemački'),
        ('fr', 'Francuski'),
        ('es', 'Španski')
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published')
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE)
    instructor = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_free = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    image = models.ImageField(upload_to='course_images/')
    enrolled_students = models.ManyToManyField(User, through='CourseEnrollment', related_name='enrolled_courses')
    is_featured = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_progress(self, user):
        if not user.is_authenticated:
            return 0
        
        total_lessons = Lesson.objects.filter(section__course=self).count()
        if total_lessons == 0:
            return 0
            
        completed_lessons = LessonCompletion.objects.filter(
            user=user,
            lesson__section__course=self
        ).count()
        
        return int((completed_lessons / total_lessons) * 100)

    def calculate_avg_rating(self):
        from django.db.models import Avg
        return self.reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    @property
    def avg_rating(self):
        if hasattr(self, '_avg_rating'):
            return self._avg_rating
        return self.calculate_avg_rating()

    @property
    def rating_stats(self):
        from django.db.models import Avg, Count
        stats = self.reviews.aggregate(
            avg=Avg('rating'),
            count=Count('id')
        )
        return {
            'average': stats['avg'] or 0,
            'count': stats['count'] or 0
        }

class CourseSection(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.course.title} - {self.title}"

class Lesson(models.Model):
    section = models.ForeignKey(CourseSection, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    content = models.TextField()
    video_url = models.URLField(blank=True, null=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

class CourseRating(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['course', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s rating for {self.course.title}"

    def can_delete(self, user):
        return user.is_staff or self.user == user

class CourseEnrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    completed = models.BooleanField(default=False)

    class Meta:
        unique_together = ('course', 'user')

    def get_progress(self):
        total_lessons = Lesson.objects.filter(section__course=self.course).count()
        if total_lessons == 0:
            return 0
            
        completed_lessons = LessonCompletion.objects.filter(
            user=self.user,
            lesson__section__course=self.course
        ).count()
        
        return int((completed_lessons / total_lessons) * 100)

    @property
    def progress(self):
        return self.get_progress()

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

class CourseDiscussion(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

class DiscussionMessage(models.Model):
    discussion = models.ForeignKey(CourseDiscussion, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

class LessonCompletion(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'lesson']

class CourseReview(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('course', 'user')

class Command(BaseCommand):
    help = 'Creates initial topics and subtopics'

    def handle(self, *args, **kwargs):
        categories = {
            'development': [
                'Razvoj web aplikacija',
                'Razvoj mobilnih aplikacija',
                'Programski jezici',
                'Razvoj igara',
            ],
            'teaching': [
                'Inženjerstvo',
                'Matematika',
                'Prirodne nauke',
                'Društvene nauke',
            ],
            'finance': [
                'Računovodstvo',
                'Kripto Valute',
                'Finansije',
                'Investiranje',
            ],
            'music': [
                'Instrumenti',
                'Muzička produkcija',
                'Pevanje',
                'Teorija muzike',
            ],
            'lifestyle': [
                'Kreativne veštine',
                'Lapota & šminka',
                'Kulinarstvo',
                'Dresiranje i briga o kućnim ljubimcima',
            ],
            'photography': [
                'Digitalna Fotografija',
                'Video Montaža',
                'Komercijalna Fotografija',
            ],
            'health': [
                'Fitnes',
                'Sport',
                'Mentalno zdravlje',
                'Nutricionizam',
            ],
            'design': [
                'Web Dizajn',
                'Grafički dizajn',
                '3D & Animacije',
                'UI/UX Dizajn',
            ],
            'marketing': [
                'Digitalni Marketing',
                'Marketing za društvene mreže',
                'Brendiranje',
                'Marketinška analitika',
            ],
            'business': [
                'Preduzetništvo',
                'Menadžment',
                'Prodaja',
            ],
            'it': [
                'Mrežna bezbednost',
                'Hardver',
                'Operativni sistemi',
                'Ostalo',
            ]
        }

        for main_cat, subtopics in categories.items():
            parent = Topic.objects.create(
                name=dict(Topic.MAIN_CATEGORIES)[main_cat],
                slug=main_cat,
                main_category=main_cat
            )
            
            for subtopic in subtopics:
                Topic.objects.create(
                    name=subtopic,
                    slug=f"{main_cat}-{slugify(subtopic)}",
                    parent=parent,
                    main_category=main_cat
                )

        self.stdout.write(self.style.SUCCESS('Successfully created topics'))

def get_topics(request):
    topics = Topic.objects.all().values('id', 'name')
    return JsonResponse(list(topics), safe=False)