import os
import django
import sys
from django.test import RequestFactory, Client
from django.urls import reverse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User
import json

user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

if not user:
    print("No users found to test with.")
    sys.exit(0)

client = Client()
client.force_login(user)

print("Testing Analytical API...")
resp = client.get(reverse('api-analytical-projects'))
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(json.dumps(resp.json(), indent=2))
else:
    print(resp.content)
