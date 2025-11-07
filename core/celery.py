# core/celery.py
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

app = Celery('core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Add Celery Beat schedule
app.conf.beat_schedule = {
    'schedule-campaigns-every-minute': {
        'task': 'campaigns.tasks.check_and_schedule_campaigns',
        'schedule': crontab(),  # Executes every minute
    },
}