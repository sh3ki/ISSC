from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0027_incidentreport_raised_to_admin'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facelogs',
            name='id_number',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                to='main.accountregistration',
                to_field='id_number',
            ),
        ),
    ]
