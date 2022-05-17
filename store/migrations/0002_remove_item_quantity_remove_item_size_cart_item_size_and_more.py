# Generated by Django 4.0.3 on 2022-05-17 18:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='item',
            name='quantity',
        ),
        migrations.RemoveField(
            model_name='item',
            name='size',
        ),
        migrations.AddField(
            model_name='cart_item',
            name='size',
            field=models.CharField(choices=[('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')], max_length=3, null=True),
        ),
        migrations.AddField(
            model_name='orderling',
            name='size',
            field=models.CharField(choices=[('XS', 'XS'), ('S', 'S'), ('M', 'M'), ('L', 'L'), ('XL', 'XL'), ('XXL', 'XXL')], max_length=3, null=True),
        ),
    ]
