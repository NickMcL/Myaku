"""Myaku Web project package."""

from ._version import __version__
# Make sure the celery app is always imported when Django starts so that
# shared_task will use this app.
from .celery import celery_app

__all__ = ('__version__', 'celery_app')
