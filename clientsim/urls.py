"""clientsim URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf.urls import url, include
from django.conf.urls.static import static
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.schemas import get_schema_view
from rest_framework.renderers import JSONOpenAPIRenderer
from client_sim import views
from clientsim import tasks
from clientsim import settings
tasks.run_tasks()

router = routers.DefaultRouter()
router.register(r'upload', views.UploadViewSet)
router.register(r'instanceautomation', views.InstanceAutomationViewSet)
router.register(r'cloudtype', views.CloudTypeViewSet)
router.register(r'cloud', views.CloudViewSet)
router.register(r'cloudimage', views.CloudImageViewSet)
router.register(r'cloudvpc', views.CloudVPCViewSet)
router.register(r'cloudsubnet', views.CloudSubnetViewSet)
router.register(r'cloudsecuritygroup', views.CloudSecurityGroupViewSet)
router.register(r'cloudinstance', views.CloudInstanceViewSet)
router.register(r'dashboard', views.DashboardViewSet)
router.register(r'dashboardlicense', views.DashboardLicenseViewSet)
router.register(r'log', views.LogViewSet)
router.register(r'networktype', views.NetworkTypeViewSet)
router.register(r'interface', views.InterfaceViewSet)
router.register(r'containertype', views.ContainerTypeViewSet)
router.register(r'container', views.ContainerViewSet)
router.register(r'network', views.NetworkViewSet)
router.register(r'app', views.AppViewSet)
router.register(r'appprofile', views.AppProfileViewSet)
router.register(r'client', views.ClientViewSet)
router.register(r'linkprofile', views.LinkProfileViewSet)
router.register(r'eventday', views.EventDayViewSet)
router.register(r'linkevent', views.LinkEventViewSet)
router.register(r'appevent', views.AppEventViewSet)

schema_view = get_schema_view(title="Client Simulator API", renderer_classes=[JSONOpenAPIRenderer])

urlpatterns = [
    path('admin/', admin.site.urls),
    path('upload/', views.upload_file),
    path('logs/', views.show_log),
    path('home/', views.show_home, name="home"),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api-token-auth/', obtain_auth_token, name='api_token_auth'),
    path('api/v0/schema/', schema_view),
    path(r'api/v0/', include(router.urls)),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
