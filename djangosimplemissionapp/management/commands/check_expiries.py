from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from djangosimplemissionapp.models import ProjectDomain, ProjectServer, Notification, User, Role

class Command(BaseCommand):
    help = 'Checks for domain and server expiries and sends notifications to SuperAdmins'

    def handle(self, *args, **options):
        today = timezone.now().date()
        thresholds = [30, 15, 7, 3, 1]
        
        # Find SuperAdmin users
        try:
            superadmin_role = Role.objects.get(name='SuperAdmin')
            superadmins = User.objects.filter(role=superadmin_role)
        except Role.DoesNotExist:
            self.stdout.write(self.style.ERROR('SuperAdmin role does not exist.'))
            # Fallback to superusers if role doesn't exist
            superadmins = User.objects.filter(is_superuser=True)

        if not superadmins.exists():
            self.stdout.write(self.style.WARNING('No SuperAdmin users found to notify.'))
            return

        self.check_domains(today, thresholds, superadmins)
        self.check_servers(today, thresholds, superadmins)

    def check_domains(self, today, thresholds, recipients):
        # Notify for any domain expiring within the next 30 days
        max_date = today + timedelta(days=30)
        expiring_domains = ProjectDomain.objects.filter(
            expiration_date__gte=today,
            expiration_date__lte=max_date
        )
        
        for domain in expiring_domains:
            days_remaining = (domain.expiration_date - today).days
            message = (
                f"Domain Expiry Alert: The domain '{domain.name}' for project "
                f"'{domain.project.name if domain.project else 'N/A'}' is expiring on "
                f"{domain.expiration_date} ({days_remaining} days remaining). "
                f"Action Required: Please contact the provider '{domain.purchased_from or 'N/A'}' "
                f"to renew the domain."
            )
            self.create_notifications(recipients, message, project=domain.project, notification_type='domain_alert')
            self.stdout.write(self.style.SUCCESS(f"Notification created for domain: {domain.name}"))

    def check_servers(self, today, thresholds, recipients):
        # Notify for any server expiring within the next 30 days
        max_date = today + timedelta(days=30)
        expiring_servers = ProjectServer.objects.filter(
            expiration_date__gte=today,
            expiration_date__lte=max_date
        )
        
        for server in expiring_servers:
            days_remaining = (server.expiration_date - today).days
            message = (
                f"Server Expiry Alert: The server '{server.name}' ({server.server_type}) for project "
                f"'{server.project.name if server.project else 'N/A'}' is expiring on "
                f"{server.expiration_date} ({days_remaining} days remaining). "
                f"Action Required: Please ensure payment is processed or contact the provider "
                f"'{server.purchased_from or 'N/A'}' to avoid service interruption."
            )
            self.create_notifications(recipients, message, project=server.project, notification_type='server_alert')
            self.stdout.write(self.style.SUCCESS(f"Notification created for server: {server.name}"))

    def create_notifications(self, recipients, message, project=None, notification_type=None):
        today = timezone.now().date()
        for user in recipients:
            # Check if a similar notification was already created today for this user
            already_exists = Notification.objects.filter(
                user=user,
                message=message,
                created_at__date=today
            ).exists()
            
            if not already_exists:
                Notification.objects.create(
                    user=user,
                    message=message,
                    project=project,
                    notification_type=notification_type
                )
