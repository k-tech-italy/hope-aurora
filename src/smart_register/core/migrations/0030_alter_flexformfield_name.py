# Generated by Django 3.2.12 on 2022-03-22 19:15

import django.contrib.postgres.fields.citext
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0029_alter_validator_target"),
    ]

    operations = [
        migrations.AlterField(
            model_name="flexformfield",
            name="name",
            field=django.contrib.postgres.fields.citext.CICharField(blank=True, max_length=100),
        ),
    ]
