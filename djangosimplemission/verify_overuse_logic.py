import os
import django
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangosimplemission.settings')
django.setup()

from djangosimplemissionapp.views import TeamPerformanceAPIView
from djangosimplemissionapp.models import Team

def test_overuse_and_remain_logic():
    view = TeamPerformanceAPIView()
    current_date = date(2026, 3, 31)
    
    # Mock a team
    mock_team = MagicMock(spec=Team)
    mock_team.id = 1
    mock_team.name = "Test Team"
    
    mock_members = MagicMock()
    mock_members.count.return_value = 0
    mock_team.members.all.return_value = mock_members
    
    # 1. Test Project: Completed, actual_end_date > deadline (Overused)
    proj_overused = MagicMock()
    proj_overused.project.name = "Project Overused"
    proj_overused.project.id = 101
    proj_overused.status = 'Completed'
    proj_overused.deadline = date(2026, 3, 24)
    proj_overused.actual_end_date = date(2026, 4, 1)
    proj_overused.start_date = date(2026, 3, 1)
    proj_overused.members.all.return_value = []
    
    # 2. Test Project: Ongoing, current_date > deadline (Overused)
    proj_ongoing_overused = MagicMock()
    proj_ongoing_overused.project.name = "Project Ongoing Overused"
    proj_ongoing_overused.project.id = 102
    proj_ongoing_overused.status = 'Progressing'
    proj_ongoing_overused.deadline = date(2026, 3, 28)
    proj_ongoing_overused.actual_end_date = None
    proj_ongoing_overused.start_date = date(2026, 3, 1)
    proj_ongoing_overused.members.all.return_value = []

    # 3. Test Project: Ongoing, current_date < deadline (Remaining)
    proj_remaining = MagicMock()
    proj_remaining.project.name = "Project Remaining"
    proj_remaining.project.id = 103
    proj_remaining.status = 'Progressing'
    proj_remaining.deadline = date(2026, 4, 5) # 5 days from March 31
    proj_remaining.actual_end_date = None
    proj_remaining.start_date = date(2026, 3, 1)
    proj_remaining.members.all.return_value = []

    with patch('djangosimplemissionapp.models.ProjectTeam.objects.filter') as mock_filter_proj, \
         patch('djangosimplemissionapp.models.ProjectServiceTeam.objects.filter') as mock_filter_svc, \
         patch('django.utils.timezone.now') as mock_now, \
         patch('djangosimplemissionapp.models.ProjectServiceMember.objects.filter') as mock_filter_mem:
        
        mock_now.return_value.date.return_value = current_date
        mock_filter_proj.return_value.select_related.return_value = [proj_overused, proj_ongoing_overused, proj_remaining]
        mock_filter_svc.return_value.select_related.return_value = []
        mock_filter_mem.return_value.filter.return_value.count.return_value = 0
        
        stats = view._get_team_stats(mock_team)
        
        print("Projects Stats:")
        for p in stats['projects']:
            print(f"Name: {p['name']}, Status: {p['status']}, Overused: {p['overused']}, Over Days: {p['over_days']}, Remain Days: {p['remain_days']}")
            
            if p['name'] == "Project Overused":
                assert p['overused'] is True
                assert p['over_days'] == 8
                assert p['remain_days'] == 0
            if p['name'] == "Project Ongoing Overused":
                assert p['overused'] is True
                assert p['over_days'] == 3
                assert p['remain_days'] == 0
            if p['name'] == "Project Remaining":
                assert p['overused'] is False
                assert p['over_days'] == 0
                assert p['remain_days'] == 5

    print("\nVerification successful!")

if __name__ == "__main__":
    test_overuse_and_remain_logic()
