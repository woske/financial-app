# Generated by Django 4.1.1 on 2023-02-02 04:17

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0008_category_monthly_budget'),
    ]

    operations = [
        migrations.CreateModel(
            name='MonthlyTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('month', models.DateField()),
                ('budget', models.DecimalField(decimal_places=2, max_digits=10)),
                ('spent', models.DecimalField(decimal_places=2, max_digits=10)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='budget.category')),
            ],
        ),
        migrations.DeleteModel(
            name='Budget',
        ),
    ]
