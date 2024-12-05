from django.contrib import admin
from .models import (
    Profile, 
    AdminOTP, 
    Topic, 
    Course, 
    CourseSection, 
    Lesson, 
    CourseRating, 
    CourseEnrollment,
    LessonCompletion
)

# We'll keep these registered for database management purposes
# but primary admin functionality will be through custom-admin views
admin.site.register(Profile)
admin.site.register(AdminOTP)
admin.site.register(Topic)
admin.site.register(Course)
admin.site.register(CourseSection)
admin.site.register(Lesson)
admin.site.register(CourseRating)
admin.site.register(CourseEnrollment)
admin.site.register(LessonCompletion)
