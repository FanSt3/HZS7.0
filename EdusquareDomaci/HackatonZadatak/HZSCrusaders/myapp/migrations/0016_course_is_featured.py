# Generated by Django 5.1.2 on 2024-12-04 17:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0015_coursereview'),
    ]

    operations = [
        migrations.AddField(
            model_name='course',
            name='is_featured',
            field=models.BooleanField(default=False),
        ),
    ]
