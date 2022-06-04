# Generated by Django 3.2.13 on 2022-05-11 13:18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0046_alter_validator_target"),
        ("registration", "0029_registration_client_validation"),
    ]

    operations = [
        migrations.AddField(
            model_name="registration",
            name="scripts",
            field=models.ManyToManyField(
                blank=True,
                limit_choices_to={"target": "script"},
                null=True,
                related_name="script_for",
                to="core.Validator",
            ),
        ),
        migrations.AlterField(
            model_name="registration",
            name="validator",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"target": "module"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="validator_for",
                to="core.validator",
            ),
        ),
    ]
