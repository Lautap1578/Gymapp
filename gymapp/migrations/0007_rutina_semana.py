from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("gymapp", "0006_payment_monto_payment_plan"),
    ]

    operations = [
        migrations.AddField(
            model_name="rutina",
            name="semana",
            field=models.PositiveSmallIntegerField(default=1),
        ),
    ]