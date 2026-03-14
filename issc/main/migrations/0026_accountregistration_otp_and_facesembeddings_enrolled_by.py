from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0025_systemconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountregistration',
            name='login_otp_code',
            field=models.CharField(blank=True, default='', max_length=10),
        ),
        migrations.AddField(
            model_name='accountregistration',
            name='login_otp_expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='accountregistration',
            name='login_otp_failed_attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='accountregistration',
            name='login_otp_locked_until',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='accountregistration',
            name='must_change_password',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='facesembeddings',
            name='enrolled_by',
            field=models.CharField(blank=True, default='', max_length=150),
        ),
    ]
