from django.core.management.base import BaseCommand
from myapp.models import Topic
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Creates initial topics and subtopics'

    def handle(self, *args, **kwargs):
        # First, delete existing topics to avoid conflicts
        Topic.objects.all().delete()
        
        # Using categories from views.py
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

        for main_cat, category_name in categories.items():
            # Create main category
            Topic.objects.create(
                name=category_name,
                category=main_cat
            )
            
            # Create subcategories
            for subtopic in subcategories[main_cat]:
                Topic.objects.create(
                    name=subtopic,
                    category=main_cat
                )

        self.stdout.write(self.style.SUCCESS('Successfully created topics')) 