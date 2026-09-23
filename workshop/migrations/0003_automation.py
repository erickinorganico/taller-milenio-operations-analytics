import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshop", "0002_analytics"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AutomationPolicy",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("automatic_enabled", models.BooleanField(default=True)),
                ("interval_minutes", models.PositiveIntegerField(default=60)),
                ("debounce_seconds", models.PositiveIntegerField(default=30)),
                ("native_enabled", models.BooleanField(default=False)),
                ("paused", models.BooleanField(default=False)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="AutomationWorkerState",
            fields=[
                ("id", models.PositiveSmallIntegerField(default=1, editable=False, primary_key=True, serialize=False)),
                ("event_cursor", models.PositiveBigIntegerField(default=0)),
                ("next_periodic_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("lease_owner", models.CharField(blank=True, max_length=120)),
                ("lease_expires_at", models.DateTimeField(blank=True, null=True)),
                ("status", models.CharField(default="idle", max_length=16)),
                ("heartbeat_at", models.DateTimeField(blank=True, null=True)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="AutomationJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("dedup_key", models.CharField(max_length=180, unique=True)),
                ("trigger", models.CharField(max_length=20)),
                ("mode", models.CharField(default="rules", max_length=12)),
                ("status", models.CharField(choices=[("pending", "Pendiente"), ("running", "En curso"), ("completed", "Completado"), ("failed", "Falló")], default="pending", max_length=12)),
                ("source_highwater", models.PositiveBigIntegerField(default=0)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("max_attempts", models.PositiveSmallIntegerField(default=3)),
                ("available_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("snapshot_id", models.CharField(blank=True, max_length=100)),
                ("agent_run_ids", models.JSONField(default=list)),
                ("result", models.JSONField(default=dict)),
                ("errors", models.JSONField(default=list)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="automation_jobs", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="automationjob",
            index=models.Index(fields=["status", "available_at", "created_at"], name="workshop_au_status_1e0fa7_idx"),
        ),
    ]
