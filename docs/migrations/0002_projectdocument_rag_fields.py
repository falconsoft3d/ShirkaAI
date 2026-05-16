from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectdocument',
            name='index_status',
            field=models.CharField(
                choices=[
                    ('pending',  'Pendiente'),
                    ('indexing', 'Indexando'),
                    ('done',     'Indexado'),
                    ('error',    'Error'),
                ],
                default='pending',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='projectdocument',
            name='chunk_count',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='projectdocument',
            name='index_error',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
