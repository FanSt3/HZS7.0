# Generated by Django 5.1.2 on 2024-12-02 18:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0005_course_language_coursediscussion_discussionmessage'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=10),
        ),
        migrations.AlterField(
            model_name='course',
            name='image',
            field=models.ImageField(upload_to='course_images/'),
        ),
        migrations.AlterField(
            model_name='course',
            name='language',
            field=models.CharField(choices=[('en', 'English'), ('sr', 'Serbian'), ('de', 'German'), ('fr', 'French'), ('es', 'Spanish')], default='en', max_length=2),
        ),
        migrations.AlterField(
            model_name='course',
            name='price',
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]
