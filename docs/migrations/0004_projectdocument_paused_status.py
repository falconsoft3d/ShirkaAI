from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0003_projectdocument_index_progress'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projectdocument',
            name='index_status',
            field=models.CharField(
                choices=[
                    ('pending',  'Pendiente'),
                    ('indexing', 'Indexando'),
                    ('paused',   'Pausado'),
                    ('done',     'Indexado'),
                    ('error',    'Error'),
                ],
                default='pending',
                max_length=10,
            ),
        ),
    ]
