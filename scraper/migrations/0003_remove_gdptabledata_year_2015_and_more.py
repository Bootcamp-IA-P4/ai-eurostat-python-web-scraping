# Generated by Django 5.1.7 on 2025-03-23 18:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0002_remove_gdptabledata_indicator'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='gdptabledata',
            name='year_2015',
        ),
        migrations.RemoveField(
            model_name='gdptabledata',
            name='year_2016',
        ),
        migrations.RemoveField(
            model_name='gdptabledata',
            name='year_2017',
        ),
        migrations.RemoveField(
            model_name='gdptabledata',
            name='year_2018',
        ),
    ]
