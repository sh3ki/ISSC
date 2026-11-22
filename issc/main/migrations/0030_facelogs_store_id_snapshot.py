from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('main', '0029_merge_0028_migrations'),
    ]

    operations = [
        migrations.AlterField(
            model_name='facelogs',
            name='id_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
