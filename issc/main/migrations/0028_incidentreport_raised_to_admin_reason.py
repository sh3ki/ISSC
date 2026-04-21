from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0027_incidentreport_raised_to_admin'),
    ]

    operations = [
        migrations.AddField(
            model_name='incidentreport',
            name='raised_to_admin_reason',
            field=models.TextField(blank=True, null=True),
        ),
    ]
