from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TemplateViewSet, AIConfigurationView

router = DefaultRouter()
router.register(r'templates', TemplateViewSet, basename='template')

urlpatterns = [
    path('templates/ai-config/', AIConfigurationView.as_view(), name='ai-config'),
    path('templates/ai-config', AIConfigurationView.as_view(), name='ai-config-no-slash'),
    path('', include(router.urls)),
]
