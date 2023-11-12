# Generated by Django 4.2.5 on 2023-10-29 17:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('asistencia', '0003_alter_aprendiz_numero_celular_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='ficha',
            name='instructores',
        ),
        migrations.AddField(
            model_name='instructor',
            name='fichas',
            field=models.ManyToManyField(to='asistencia.ficha'),
        ),
    ]
