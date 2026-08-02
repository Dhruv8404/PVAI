from django.db import migrations, models
import django.db.models.deletion
import uuid

class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='HtmlTemplate',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=100)),
                ('version', models.CharField(default='1.0.0', max_length=20)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('html_file', models.CharField(max_length=255)),
                ('is_active', models.BooleanField(default=False)),
                ('is_deleted', models.BooleanField(default=False)),
                ('uploaded_by', models.EmailField(blank=True, max_length=254, null=True)),
                ('preview_image', models.CharField(blank=True, max_length=255, null=True)),
                ('status', models.CharField(choices=[('Draft', 'Draft'), ('Processing', 'Processing'), ('Ready', 'Ready'), ('Failed', 'Failed'), ('Active', 'Active'), ('Inactive', 'Inactive')], default='Draft', max_length=20)),
                ('required_files', models.JSONField(blank=True, default=list, help_text='List of required excel file types')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'html_templates',
                'unique_together': {('name', 'version', 'is_deleted')},
            },
        ),
        migrations.CreateModel(
            name='AIConfiguration',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('embedding_model', models.CharField(default='BAAI/bge-small-en-v1.5', max_length=100)),
                ('embedding_dimension', models.PositiveIntegerField(default=384)),
                ('collection_name', models.CharField(default='template_fields', max_length=100)),
                ('similarity_threshold', models.FloatField(default=0.9)),
                ('llm_threshold', models.FloatField(default=0.7)),
                ('llm_model', models.CharField(default='gpt-4o', max_length=50)),
                ('fallback_enabled', models.BooleanField(default=True)),
                ('cache_enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'ai_configurations',
            },
        ),
        migrations.CreateModel(
            name='TemplateField',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('field_name', models.CharField(max_length=100)),
                ('description', models.CharField(blank=True, max_length=255, null=True)),
                ('required', models.BooleanField(default=True)),
                ('data_type', models.CharField(choices=[('string', 'String'), ('integer', 'Integer'), ('float', 'Float'), ('date', 'Date'), ('boolean', 'Boolean'), ('enum', 'Enum')], default='string', max_length=20)),
                ('examples', models.JSONField(blank=True, default=list, help_text='List of example field values')),
                ('aliases', models.JSONField(blank=True, default=list, help_text='Alternative names or headers')),
                ('chroma_document_id', models.CharField(blank=True, max_length=255, null=True)),
                ('embedding_status', models.CharField(choices=[('Pending', 'Pending'), ('Completed', 'Completed'), ('Failed', 'Failed')], default='Pending', max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='fields', to='django_reference.htmltemplate')),
            ],
            options={
                'db_table': 'template_fields',
                'unique_together': {('template', 'field_name')},
            },
        ),
    ]
