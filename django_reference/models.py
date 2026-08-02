from django.db import models
import uuid

class HtmlTemplate(models.Model):
    STATUS_CHOICES = [
        ('Draft', 'Draft'),
        ('Processing', 'Processing'),
        ('Ready', 'Ready'),
        ('Failed', 'Failed'),
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=20, default='1.0.0')
    description = models.CharField(max_length=255, blank=True, null=True)
    html_file = models.CharField(max_length=255)  # File path or URL
    is_active = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    uploaded_by = models.EmailField(blank=True, null=True)
    preview_image = models.CharField(max_length=255, blank=True, null=True)
    
    # Manifest-driven columns
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Draft')
    required_files = models.JSONField(default=list, blank=True, help_text="List of required excel file types")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'html_templates'
        unique_together = ('name', 'version', 'is_deleted')

    def __str__(self):
        return f"{self.name} (v{self.version}) - {self.status}"


class TemplateField(models.Model):
    DATA_TYPE_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('date', 'Date'),
        ('boolean', 'Boolean'),
        ('enum', 'Enum'),
    ]

    EMBEDDING_STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    template = models.ForeignKey(HtmlTemplate, on_delete=models.CASCADE, related_name='fields')
    field_name = models.CharField(max_length=100)
    description = models.CharField(max_length=255, blank=True, null=True)
    required = models.BooleanField(default=True)
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default='string')
    examples = models.JSONField(default=list, blank=True, help_text="List of example field values")
    aliases = models.JSONField(default=list, blank=True, help_text="Alternative names or headers")
    chroma_document_id = models.CharField(max_length=255, blank=True, null=True)
    embedding_status = models.CharField(max_length=20, choices=EMBEDDING_STATUS_CHOICES, default='Pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'template_fields'
        unique_together = ('template', 'field_name')

    def __str__(self):
        return f"{self.field_name} ({self.data_type}) - Template: {self.template.name}"


class AIConfiguration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    embedding_model = models.CharField(max_length=100, default='BAAI/bge-small-en-v1.5')
    embedding_dimension = models.PositiveIntegerField(default=384)
    collection_name = models.CharField(max_length=100, default='template_fields')
    similarity_threshold = models.FloatField(default=0.90)
    llm_threshold = models.FloatField(default=0.70)
    llm_model = models.CharField(max_length=50, default='gpt-4o')
    fallback_enabled = models.BooleanField(default=True)
    cache_enabled = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ai_configurations'

    def __str__(self):
        return f"AI Settings - {self.embedding_model}"
