from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('llm_models', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='llmmodel',
            name='public',
            field=models.BooleanField(default=False, help_text='Visible en el home público para cualquier visitante'),
        ),
    ]
