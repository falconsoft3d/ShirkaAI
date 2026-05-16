from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('docs', '0002_projectdocument_rag_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='projectdocument',
            name='index_progress',
            field=models.IntegerField(default=0),
        ),
    ]
