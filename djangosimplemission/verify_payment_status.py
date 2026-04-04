import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectService, ProjectServer, ProjectDomain
from djangosimplemissionapp.serializers import ProjectServiceSerializer, ProjectServerSerializer, ProjectDomainSerializer

def verify_payment_status():
    print("Verifying payment_status field in serializers...")
    
    # Create a dummy project first
    proj = Project.objects.create(name="Test Project", description="Test Description")
    
    # 1. Test ProjectService
    service = ProjectService.objects.create(project=proj, name="Test Service", payment_status="PAID")
    ser_service = ProjectServiceSerializer(instance=service)
    if 'payment_status' in ser_service.data:
        print(f"✅ ProjectServiceSerializer included payment_status: {ser_service.data['payment_status']}")
    else:
        print("❌ ProjectServiceSerializer MISSING payment_status")

    # 2. Test ProjectServer
    server = ProjectServer.objects.create(project=proj, name="Test Server", payment_status="UNPAID")
    ser_server = ProjectServerSerializer(instance=server)
    if 'payment_status' in ser_server.data:
        print(f"✅ ProjectServerSerializer included payment_status: {ser_server.data['payment_status']}")
    else:
        print("❌ ProjectServerSerializer MISSING payment_status")

    # 3. Test ProjectDomain
    domain = ProjectDomain.objects.create(project=proj, name="example.com", payment_status="PAID")
    ser_domain = ProjectDomainSerializer(instance=domain)
    if 'payment_status' in ser_domain.data:
        print(f"✅ ProjectDomainSerializer included payment_status: {ser_domain.data['payment_status']}")
    else:
        print("❌ ProjectDomainSerializer MISSING payment_status")
    
    # Cleanup
    proj.delete()

if __name__ == "__main__":
    verify_payment_status()
