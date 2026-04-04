import os
import django
from rest_framework import serializers

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import Project, ProjectBusinessAddress
from djangosimplemissionapp.serializers import ProjectSerializer

def debug_serializer():
    addr = ProjectBusinessAddress.objects.create(legal_name="Test")
    data = {
        "name": "Debug Project",
        "description": "Some description", # Added because it's required in model
        "project_business_addresses": [{"id": addr.id}]
    }
    print(f"Input Data: {data}")
    ser = ProjectSerializer(data=data)
    
    # Inspect the field
    field = ser.fields.get('project_business_addresses')
    if field:
        print(f"Field 'project_business_addresses' - Required: {field.required}, Allow Null: {field.allow_null}")
    
    print(f"Is Valid? {ser.is_valid()}")
    if not ser.is_valid():
        print(f"Errors: {ser.errors}")

if __name__ == "__main__":
    debug_serializer()
