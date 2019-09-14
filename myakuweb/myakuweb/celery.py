"""Celery app setup for MyakuWeb."""

import os

from celery import Celery

from myaku import utils

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myakuweb.settings')

rabbit_host = os.environ.get('RABBIT_HOST', None)
if rabbit_host is not None:
    rabbit_username = utils.get_value_from_env_file('RABBIT_USERNAME_FILE')
    rabbit_password = utils.get_value_from_env_file('RABBIT_PASSWORD_FILE')
    rabbit_url = (
        f'amqp://{rabbit_username}:{rabbit_password}@{rabbit_host}:5672/'
    )
else:
    rabbit_url = 'amqp://'

celery_app = Celery('myakuweb', broker=rabbit_url)

celery_app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
celery_app.autodiscover_tasks()


@celery_app.task(bind=True)
def debug_task(self):
    """Print the celery request."""
    print(f'Request: {self.request!r}')
