import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectBusinessAddress
from djangosimplemissionapp.serializers import ProjectSerializer

def test_shared_address():
    print("Testing Shared Address logic...")
    
    # 1. Create a single business address (Client)
    print("Creating one client address...")
    client_addr = ProjectBusinessAddress.objects.create(legal_name="Global Client Corp", city="London")
    addr_id = client_addr.id
    print(f"Client Address ID: {addr_id}")

    # 2. Create Project 1 and link to this address
    print("Creating Project 1 via Serializer...")
    p1_data = {
        "name": "Project Alpha",
        "description": "First project for client",
        "business_address": {"id": addr_id}
    }
    s1 = ProjectSerializer(data=p1_data)
    if s1.is_valid():
        p1 = s1.save()
        print(f"Project 1 created with ID: {p1.id}, Link: {p1.business_address.id}")
    else:
        print(f"Error P1: {s1.errors}")
        return

    # 3. Create Project 2 and link to SAME address
    print("Creating Project 2 via Serializer...")
    p2_data = {
        "name": "Project Beta",
        "description": "Second project for client",
        "business_address": {"id": addr_id}
    }
    s2 = ProjectSerializer(data=p2_data)
    if s2.is_valid():
        p2 = s2.save()
        print(f"Project 2 created with ID: {p2.id}, Link: {p2.business_address.id}")
    else:
        print(f"Error P2: {s2.errors}")
        return

    # 4. Verify 1 -> Many
    print("\nVerifying Relationship...")
    client_addr.refresh_from_db()
    linked_projects = client_addr.projects.all()
    print(f"Address '{client_addr.legal_name}' is now linked to {linked_projects.count()} projects.")
    for p in linked_projects:
        print(f" - {p.name}")

    if linked_projects.count() == 2:
        print("\n✅ SUCCESS: One business address shared across multiple projects!")
    else:
        print("\n❌ FAILURE: Relationship logic error.")

    # Cleanup
    # p1.delete()
    # p2.delete()
    # client_addr.delete()

if __name__ == "__main__":
    test_shared_address()
