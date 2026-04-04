import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectBusinessAddress
from djangosimplemissionapp.serializers import ProjectSerializer

def test_id_stability():
    # 1. Setup a project with an address
    print("Setting up test project and address...")
    proj = Project.objects.create(name="Stability Test Project")
    addr = ProjectBusinessAddress.objects.create(project=proj, legal_name="Initial Name", city="Initial City")
    original_id = addr.id
    print(f"Initial Address ID: {original_id}")

    # 2. Simulate an update via Serializer (exactly how the API does it)
    print("Simulating update via ProjectSerializer...")
    data = {
        "name": "Updated Project Name",
        "project_business_addresses": [
            {
                "id": original_id,
                "legal_name": "Updated Legal Name",
                "city": "Updated City"
            }
        ]
    }
    
    serializer = ProjectSerializer(instance=proj, data=data, partial=True)
    if serializer.is_valid():
        serializer.save()
        print("Update successful.")
    else:
        print(f"Update failed: {serializer.errors}")
        return

    # 3. Verify ID
    proj.refresh_from_db()
    new_addr = proj.project_business_addresses.first()
    
    if new_addr and new_addr.id == original_id:
        print(f"✅ SUCCESS: ID remained {original_id}")
        print(f"Updated Name: {new_addr.legal_name}")
    else:
        print(f"❌ FAILURE: ID changed from {original_id} to {new_addr.id if new_addr else 'None'}")

    # Cleanup
    proj.delete()

if __name__ == "__main__":
    test_id_stability()
