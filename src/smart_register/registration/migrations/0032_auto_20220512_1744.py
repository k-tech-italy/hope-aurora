# Generated by Django 3.2.13 on 2022-05-12 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registration", "0031_auto_20220512_1125"),
    ]

    operations = [
        migrations.AddField(
            model_name="record",
            name="unique_field",
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="registration",
            name="unique_field",
            field=models.CharField(
                blank=True, help_text="Form field to be used as unique key", max_length=255, null=True
            ),
        ),
        migrations.AlterUniqueTogether(
            name="record",
            unique_together={("registration", "unique_field")},
        ),
    ]
