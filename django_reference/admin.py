from django.contrib import admin
from django.utils.html import format_html
from .models import HtmlTemplate, TemplateField, AIConfiguration

class TemplateFieldInline(admin.TabularInline):
    model = TemplateField
    extra = 0
    fields = ['field_name', 'data_type', 'required', 'embedding_status', 'chroma_document_id']
    readonly_fields = ['chroma_document_id', 'embedding_status']


@admin.register(HtmlTemplate)
class HtmlTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'status_badge', 'is_active', 'uploaded_by', 'created_at']
    list_filter = ['status', 'is_active', 'is_deleted']
    search_fields = ['name', 'version', 'uploaded_by']
    inlines = [TemplateFieldInline]
    
    actions = ['activate_selected_templates', 'deactivate_selected_templates']

    def status_badge(self, obj):
        color_map = {
            'Draft': '#6B7280',      # Grey
            'Processing': '#3B82F6', # Blue
            'Ready': '#10B981',      # Green
            'Failed': '#EF4444',     # Red
            'Active': '#047857',     # Deep Green
            'Inactive': '#374151'    # Dark Grey
        }
        color = color_map.get(obj.status, '#000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 4px; font-weight: bold;">{}</span>',
            color,
            obj.status
        )
    status_badge.short_description = 'Status'

    def activate_selected_templates(self, request, queryset):
        for template in queryset:
            try:
                from .services import template_service
                template_service.update_template_status(template.id, True)
            except Exception as e:
                self.message_user(request, f"Failed to activate '{template.name}': {str(e)}", level='ERROR')
    activate_selected_templates.short_description = "Activate selected templates"

    def deactivate_selected_templates(self, request, queryset):
        for template in queryset:
            try:
                from .services import template_service
                template_service.update_template_status(template.id, False)
            except Exception as e:
                self.message_user(request, f"Failed to deactivate '{template.name}': {str(e)}", level='ERROR')
    deactivate_selected_templates.short_description = "Deactivate selected templates"


@admin.register(TemplateField)
class TemplateFieldAdmin(admin.ModelAdmin):
    list_display = ['field_name', 'template', 'data_type', 'required', 'embedding_status', 'chroma_document_id']
    list_filter = ['data_type', 'required', 'embedding_status']
    search_fields = ['field_name', 'template__name', 'chroma_document_id']


@admin.register(AIConfiguration)
class AIConfigurationAdmin(admin.ModelAdmin):
    list_display = ['embedding_model', 'embedding_dimension', 'collection_name', 'similarity_threshold', 'llm_threshold', 'llm_model']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def has_add_permission(self, request):
        # Prevent creating multiple configurations, keep it singleton
        return not AIConfiguration.objects.exists()
