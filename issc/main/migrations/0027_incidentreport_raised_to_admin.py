from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0026_accountregistration_otp_and_facesembeddings_enrolled_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='incidentreport',
            name='raised_to_admin',
            field=models.BooleanField(default=False),
        ),
    ]
