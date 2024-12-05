# Generated by Django 5.1.2 on 2024-12-05 17:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0017_alter_course_language_alter_topic_category'),
    ]

    operations = [
        migrations.AlterField(
            model_name='topic',
            name='category',
            field=models.CharField(choices=[('development', 'Razvoj softvera'), ('business', 'Biznis'), ('finance', 'Finansije & Računovodstvo'), ('it', 'Infomracione tehnologije'), ('design', 'Dizajn'), ('marketing', 'Marketing'), ('lifestyle', 'Lifestyle'), ('photography', 'Fotografija & Video'), ('health', 'Zdravlje & Sport'), ('music', 'Muzika'), ('teaching', 'Teaching & Academics')], default='development', max_length=50),
        ),
    ]