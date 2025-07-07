from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
import multiprocessing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_root.settings')
app = Celery('project_root')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

app.autodiscover_tasks(lambda: ['autoemail'])
multiprocessing.set_start_method('spawn', force=True)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
