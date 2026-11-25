from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("workshop", "0008_reception_receipt")]

    operations = [
        migrations.AddField(
            model_name="inspection", name="submission_key",
            field=models.UUIDField(blank=True, editable=False, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="inspection", name="submission_digest",
            field=models.CharField(blank=True, editable=False, max_length=64),
        ),
    ]
