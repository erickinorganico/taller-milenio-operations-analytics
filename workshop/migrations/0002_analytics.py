from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    dependencies = [
        ("workshop", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AnalyticsSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("recorded_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("trigger", models.CharField(default="manual", max_length=32)),
                ("source_fingerprint", models.CharField(max_length=64)),
                ("audit_cursor", models.BigIntegerField(default=0)),
                ("source_counts", models.JSONField(default=dict)),
                ("freshness", models.JSONField(default=dict)),
                ("source_refs", models.JSONField(default=dict)),
                ("summary", models.JSONField(default=dict)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                             related_name="analytics_snapshots", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-recorded_at", "-pk"]},
        ),
        migrations.CreateModel(
            name="AnalyticsRow",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("mart", models.CharField(db_index=True, max_length=40)),
                ("key", models.CharField(max_length=160)),
                ("data", models.JSONField(default=dict)),
                ("snapshot", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                                                related_name="rows", to="workshop.analyticssnapshot")),
            ],
            options={"ordering": ["mart", "key", "pk"]},
        ),
        migrations.AddConstraint(
            model_name="analyticsrow",
            constraint=models.UniqueConstraint(fields=("snapshot", "mart", "key"), name="uniq_analytics_snapshot_mart_key"),
        ),
        migrations.AddIndex(
            model_name="analyticsrow",
            index=models.Index(fields=["snapshot", "mart"], name="workshop_an_snapsho_6860e3_idx"),
        ),
    ]
