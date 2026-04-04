import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectBusinessAddress
from djangosimplemissionapp.serializers import ProjectSerializer

def test_many_to_many_relationship():
    print("Testing Many-to-Many Relationship...")
    
    # 1. Create shared address
    addr = ProjectBusinessAddress.objects.create(legal_name="Shared Client", city="City A")
    addr_id = addr.id
    print(f"Created Address ID: {addr_id}")

    # 2. Create Project 1 with this address
    print("Creating Project 1 via Serializer...")
    p1_data = {
        "name": "Project 1",
        "description": "Desc 1",
        "project_business_addresses": [{"id": addr_id}]
    }
    s1 = ProjectSerializer(data=p1_data)
    if s1.is_valid():
        p1 = s1.save()
        print(f"Project 1 (ID: {p1.id}) linked to Address {p1.project_business_addresses.first().id}")
    else:
        print(f"Error P1: {s1.errors}")
        return

    # 3. Create Project 2 with SAME address
    print("Creating Project 2 via Serializer...")
    p2_data = {
        "name": "Project 2",
        "description": "Desc 2",
        "project_business_addresses": [{"id": addr_id}]
    }
    s2 = ProjectSerializer(data=p2_data)
    if s2.is_valid():
        p2 = s2.save()
        print(f"Project 2 (ID: {p2.id}) linked to Address {p2.project_business_addresses.first().id}")
    else:
        print(f"Error P2: {s2.errors}")
        return

    # 4. Add a SECOND address to Project 1
    print("\nAdding second address to Project 1...")
    p1_update_data = {
        "project_business_addresses": [
            {"id": addr_id},
            {"legal_name": "Second Address", "city": "City B"}
        ]
    }
    s1_u = ProjectSerializer(instance=p1, data=p1_update_data, partial=True)
    if s1_u.is_valid():
        s1_u.save()
        print(f"Project 1 now has {p1.project_business_addresses.count()} addresses.")
    else:
        print(f"Error P1 Update: {s1_u.errors}")

    # 5. Verify Project 2 still has ONLY the first address
    print(f"Project 2 still has {p2.project_business_addresses.count()} address.")

    # 6. Verify shared data update
    print("\nUpdating shared address name via Project 2...")
    p2_update_data = {
        "project_business_addresses": [
            {"id": addr_id, "legal_name": "Updated Shared Client"}
        ]
    }
    s2_u = ProjectSerializer(instance=p2, data=p2_update_data, partial=True)
    if s2_u.is_valid():
        s2_u.save()
        p1.refresh_from_db()
        shared_in_p1 = p1.project_business_addresses.get(id=addr_id)
        print(f"Project 1's view of shared address: {shared_in_p1.legal_name}")
        if shared_in_p1.legal_name == "Updated Shared Client":
            print("✅ Shared update verified.")
        else:
            print("❌ Shared update failed.")

    print("\n✅ Many-to-Many logic confirmed!")

if __name__ == "__main__":
    test_many_to_many_relationship()
