# Generated by Django 5.1.2 on 2024-12-02 18:16

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0006_course_status_alter_course_image_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='topic',
            options={'ordering': ['name']},
        ),
        migrations.RemoveField(
            model_name='topic',
            name='icon',
        ),
        migrations.AddField(
            model_name='topic',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='topic',
            name='main_category',
            field=models.CharField(choices=[('technology', 'Technology'), ('school', 'School'), ('finance', 'Finance'), ('music', 'Music'), ('lifestyle', 'Lifestyle'), ('video_photo', 'Video & Photography')], default='technology', max_length=20),
        ),
        migrations.AddField(
            model_name='topic',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='subtopics', to='myapp.topic'),
        ),
        migrations.AlterField(
            model_name='topic',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='topic',
            name='name',
            field=models.CharField(max_length=200),
        ),
    ]
