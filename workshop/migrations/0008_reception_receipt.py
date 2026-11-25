import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("workshop", "0007_photo_ai_controls"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReceptionReceipt",
            fields=[
                ("token", models.UUIDField(editable=False, primary_key=True, serialize=False)),
                ("step", models.CharField(max_length=12)),
                ("next_url", models.CharField(max_length=200)),
                ("actor", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
