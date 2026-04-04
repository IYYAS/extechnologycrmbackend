from django.utils import timezone
from datetime import timedelta, datetime
from django.db.models import Q

def get_date_filter_q(filter_type, date_field='start_date', start_date_str=None, end_date_str=None):
    """
    Returns a Django Q object for date filtering based on common ranges.
    """
    today = timezone.now().date()
    filter_type = (filter_type or 'today').lower()
    
    if filter_type == 'all':
        return Q()

    if filter_type == 'today':
        return Q(**{f'{date_field}': today})
    
    elif filter_type == 'this_week':
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        return Q(**{f'{date_field}__range': [start_of_week, end_of_week]})
    
    elif filter_type == 'this_month':
        start_of_month = today.replace(day=1)
        if today.month == 12:
            end_of_month = start_of_month.replace(year=today.year + 1, month=1) - timedelta(days=1)
        else:
            end_of_month = start_of_month.replace(month=today.month + 1) - timedelta(days=1)
        return Q(**{f'{date_field}__range': [start_of_month, end_of_month]})
    
    elif filter_type == 'this_year':
        start_of_year = today.replace(month=1, day=1)
        end_of_year = today.replace(month=12, day=31)
        return Q(**{f'{date_field}__range': [start_of_year, end_of_year]})
    
    elif filter_type == 'custom':
        if not start_date_str or not end_date_str:
            return None, "For custom filter, both start_date and end_date are required (format: YYYY-MM-DD)"
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            if start_date > end_date:
                return None, "start_date must be before end_date"
            
            return Q(**{f'{date_field}__range': [start_date, end_date]}), None
        except ValueError:
            return None, "Invalid date format. Please use YYYY-MM-DD"
    
    return Q(), "Invalid filter type"
def calculate_performance_metrics(activities):
    """
    Calculates average progress, target progress, and efficiency from a list of activities.
    """
    total = len(activities)
    if total == 0:
        return {
            "avg_progress": 0,
            "avg_target": 0,
            "efficiency": 0,
            "total_activities": 0
        }
    
    actual_sum = sum(100 - (a.pending_work_percentage or 0) for a in activities)
    target_sum = sum(getattr(a, 'target_work_percentage', 0) for a in activities)
    
    avg_progress = float(actual_sum) / total
    avg_target = float(target_sum) / total
    efficiency = (float(actual_sum) / float(target_sum) * 100) if target_sum > 0 else 0
    
    return {
        "avg_progress": round(avg_progress, 2),
        "avg_target": round(avg_target, 2),
        "efficiency": round(efficiency, 2),
        "total_activities": total
    }
