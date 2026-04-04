import os
import django
import sys
from django.test import RequestFactory, Client
from django.urls import reverse

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.models import User

# Try to find an admin user to test with
user = User.objects.filter(is_superuser=True).first()
if not user:
    user = User.objects.first()

if not user:
    print("No users found to test with.")
    sys.exit(0)

client = Client()
client.force_login(user)

print("Testing Income Statement JSON...")
resp = client.get(reverse('api-income-statement'))
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(resp.json())

print("\nTesting Cash Flow Statement JSON...")
resp = client.get(reverse('api-cash-flow'))
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(resp.json())

print("\nTesting Balance Sheet JSON...")
resp = client.get(reverse('api-balance-sheet'))
print(f"Status: {resp.status_code}")
if resp.status_code == 200:
    print(resp.json())

print("\nTesting Income Statement PDF...")
resp = client.get(reverse('api-income-statement') + '?format=pdf')
print(f"Status: {resp.status_code}")
print(f"Content-Type: {resp['Content-Type']}")
