from rest_framework import viewsets, status, views
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from .models import HtmlTemplate, TemplateField, AIConfiguration
from .serializers import (
    HtmlTemplateSerializer, 
    HtmlTemplateDetailSerializer, 
    TemplateManifestSubmitSerializer, 
    TemplateFieldSerializer,
    AIConfigurationSerializer
)
from .services import template_service


class TemplateViewSet(viewsets.ViewSet):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def list(self, request):
        """GET /api/templates/ - List all templates."""
        templates = HtmlTemplate.objects.filter(is_deleted=False).order_by('-created_at')
        serializer = HtmlTemplateSerializer(templates, many=True)
        return Response({
            "success": True,
            "message": "Fetched templates successfully",
            "data": serializer.data
        })

    def create(self, request):
        """POST /api/templates/ - Step 1: Upload template draft."""
        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response({"success": False, "detail": "Missing template HTML file."}, status=status.HTTP_400_BAD_REQUEST)
            
        name = request.data.get('name')
        version = request.data.get('version', '1.0.0')
        description = request.data.get('description', '')

        if not name:
            return Response({"success": False, "detail": "Missing template name."}, status=status.HTTP_400_BAD_REQUEST)

        # Basic HTML extension check
        if not file_obj.name.lower().endswith('.html'):
            return Response({"success": False, "detail": "Only HTML templates (.html) are allowed."}, status=status.HTTP_400_BAD_REQUEST)

        # Save draft local file simulation
        os_dir = "storage/templates"
        os.makedirs(os_dir, exist_ok=True)
        local_path = os.path.join(os_dir, file_obj.name)
        with open(local_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        try:
            template = template_service.create_template_draft(
                name=name,
                version=version,
                description=description,
                html_file_path=local_path,
                uploaded_by=request.user.email if request.user and request.user.is_authenticated else "admin@company.com"
            )
            serializer = HtmlTemplateSerializer(template)
            return Response({
                "success": True,
                "message": "Template draft uploaded successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        except ValidationError as ve:
            return Response({"success": False, "detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def retrieve(self, request, pk=None):
        """GET /api/templates/{id}/ - Retrieve full template details."""
        template = get_object_or_404(HtmlTemplate, id=pk, is_deleted=False)
        serializer = HtmlTemplateDetailSerializer(template)
        return Response({
            "success": True,
            "message": "Fetched HTML template details successfully",
            "data": serializer.data
        })

    def destroy(self, request, pk=None):
        """DELETE /api/templates/{id}/ - Soft delete template and wipe embeddings."""
        get_object_or_404(HtmlTemplate, id=pk, is_deleted=False)
        try:
            template_service.delete_template(pk)
            return Response({
                "success": True,
                "message": "HTML Template deleted successfully",
                "data": {}
            })
        except Exception as e:
            return Response({"success": False, "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='manifest')
    def submit_manifest(self, request, pk=None):
        """POST /api/templates/{id}/manifest/ - Step 2: Submit manifest fields form."""
        get_object_or_404(HtmlTemplate, id=pk, is_deleted=False)
        serializer = TemplateManifestSubmitSerializer(data=request.data)
        if not serializer.is_validate():
            serializer.is_valid(raise_exception=True)
            
        validated_data = serializer.validated_data
        try:
            template = template_service.submit_template_manifest(
                template_id=pk,
                required_excel_files=validated_data["required_excel_files"],
                required_fields=validated_data["required_fields"]
            )
            return Response({
                "success": True,
                "message": "Manifest registered successfully. Embeddings loading in background.",
                "data": HtmlTemplateSerializer(template).data
            })
        except ValidationError as ve:
            return Response({"success": False, "detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='fields')
    def get_fields(self, request, pk=None):
        """GET /api/templates/{id}/fields/ - Return required fields list."""
        template = get_object_or_404(HtmlTemplate, id=pk, is_deleted=False)
        fields = template.fields.all()
        serializer = TemplateFieldSerializer(fields, many=True)
        return Response({
            "success": True,
            "message": "Fetched template required fields successfully",
            "data": serializer.data
        })

    @action(detail=True, methods=['patch'], url_path='status')
    def patch_status(self, request, pk=None):
        """PATCH /api/templates/{id}/status/ - Activate/Deactivate template."""
        get_object_or_404(HtmlTemplate, id=pk, is_deleted=False)
        is_active = request.data.get('is_active')
        if is_active is None:
            return Response({"success": False, "detail": "Missing is_active boolean value."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            template = template_service.update_template_status(pk, is_active)
            return Response({
                "success": True,
                "message": f"Template status updated to {'Active' if is_active else 'Inactive'}",
                "data": HtmlTemplateSerializer(template).data
            })
        except ValidationError as ve:
            return Response({"success": False, "detail": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIConfigurationView(views.APIView):
    def get(self, request):
        """GET /api/templates/ai-config/ - Get AI config settings."""
        config = template_service.get_ai_config()
        serializer = AIConfigurationSerializer(config)
        return Response({
            "success": True,
            "message": "Fetched AI configurations successfully",
            "data": serializer.data
        })

    def put(self, request):
        """PUT /api/templates/ai-config/ - Update AI config settings."""
        serializer = AIConfigurationSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            config = template_service.update_ai_config(serializer.validated_data)
            return Response({
                "success": True,
                "message": "AI configurations updated successfully",
                "data": AIConfigurationSerializer(config).data
            })
        except Exception as e:
            return Response({"success": False, "detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
