# Generated by Django 3.2.12 on 2022-03-09 12:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("registration", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="registration",
            name="public_key",
            field=models.TextField(blank=True, null=True),
        ),
    ]
