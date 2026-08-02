from rest_framework import serializers
from .models import HtmlTemplate, TemplateField, AIConfiguration

class TemplateFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateField
        fields = [
            'id', 'field_name', 'description', 'required', 
            'data_type', 'examples', 'aliases', 
            'chroma_document_id', 'embedding_status', 'created_at'
        ]


class HtmlTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = HtmlTemplate
        fields = [
            'id', 'name', 'version', 'description', 'html_file', 
            'is_active', 'status', 'required_files', 
            'uploaded_by', 'created_at', 'updated_at'
        ]


class HtmlTemplateDetailSerializer(serializers.ModelSerializer):
    fields = TemplateFieldSerializer(many=True, read_only=True)
    html_content = serializers.SerializerMethodField()

    class Meta:
        model = HtmlTemplate
        fields = [
            'id', 'name', 'version', 'description', 'html_file', 
            'is_active', 'status', 'required_files', 
            'uploaded_by', 'created_at', 'updated_at', 
            'html_content', 'fields'
        ]

    def get_html_content(self, obj) -> str:
        # Graceful file reader for template content
        import os
        if os.path.exists(obj.html_file):
            try:
                with open(obj.html_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
        return "<h1>Template Content Unreadable on Disk</h1>"


class ManifestFieldSubmitSerializer(serializers.Serializer):
    field_name = serializers.CharField(max_length=100)
    description = serializers.CharField(max_length=255, required=False, allow_blank=True, allow_null=True)
    required = serializers.BooleanField(default=True)
    data_type = serializers.ChoiceField(choices=TemplateField.DATA_TYPE_CHOICES, default='string')
    examples = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    aliases = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class TemplateManifestSubmitSerializer(serializers.Serializer):
    required_excel_files = serializers.ListField(child=serializers.CharField())
    required_fields = ManifestFieldSubmitSerializer(many=True)


class AIConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIConfiguration
        fields = [
            'id', 'embedding_model', 'embedding_dimension', 'collection_name', 
            'similarity_threshold', 'llm_threshold', 'llm_model', 
            'fallback_enabled', 'cache_enabled', 'created_at', 'updated_at'
        ]
