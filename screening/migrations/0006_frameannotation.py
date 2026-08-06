import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('screening', '0005_auto_20260320_1655'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='FrameAnnotation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quadrant', models.CharField(choices=[('RU', 'Right-Upper'), ('RL', 'Right-Lower'), ('LU', 'Left-Upper'), ('LL', 'Left-Lower')], max_length=2)),
                ('frame_index', models.PositiveSmallIntegerField()),
                ('image_type', models.CharField(choices=[('visual', 'Visual'), ('thermal', 'Thermal')], max_length=10)),
                ('marker_x', models.FloatField(help_text='X position as percentage 0–100')),
                ('marker_y', models.FloatField(help_text='Y position as percentage 0–100')),
                ('note', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('attachment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='frame_annotations', to='screening.screeningattachment')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='frame_annotations', to=settings.AUTH_USER_MODEL)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='frame_annotations', to='screening.screeningsession')),
            ],
            options={
                'verbose_name': 'frame annotation',
                'verbose_name_plural': 'frame annotations',
                'ordering': ['-created_at'],
            },
        ),
    ]
