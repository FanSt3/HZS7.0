from django.core.management.base import BaseCommand
from myapp.models import Topic
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Creates initial topics and subtopics'

    def handle(self, *args, **kwargs):
        # First, delete existing topics to avoid conflicts
        Topic.objects.all().delete()
        
        categories = {
            'technology': [
                'Web Development',
                'Mobile Development',
                'Data Science',
                'Cybersecurity',
                'AI & Machine Learning',
                'Cloud Computing',
                'DevOps'
            ],
            'school': [
                'Mathematics',
                'Physics',
                'Chemistry',
                'Biology',
                'Literature',
                'History'
            ],
            'finance': [
                'Investment',
                'Cryptocurrency',
                'Personal Finance',
                'Stock Trading',
                'Business Finance'
            ],
            'music': [
                'Guitar',
                'Piano',
                'Music Theory',
                'Music Production',
                'Singing'
            ],
            'lifestyle': [
                'Fitness',
                'Cooking',
                'Personal Development',
                'Meditation',
                'Art & Design'
            ],
            'video_photo': [
                'Photography',
                'Video Editing',
                'Animation',
                'Cinematography',
                'Digital Art'
            ]
        }

        for main_cat, subtopics in categories.items():
            # Create main category
            parent = Topic.objects.create(
                name=dict(Topic.MAIN_CATEGORIES)[main_cat],
                slug=main_cat,
                main_category=main_cat
            )
            
            # Create subtopics
            for subtopic in subtopics:
                Topic.objects.create(
                    name=subtopic,
                    slug=f"{main_cat}-{slugify(subtopic)}",
                    parent=parent,
                    main_category=main_cat
                )

        self.stdout.write(self.style.SUCCESS('Successfully created topics')) % 