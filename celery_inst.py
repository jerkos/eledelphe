__author__ = 'Marc'

import os

from celery import Celery

CLOUDAMQP_URL = os.environ.get('CLOUDAMQP_URL')
if not CLOUDAMQP_URL:
    CLOUDAMQP_URL = 'amqp://'

celery = Celery('eledelphe',
                broker=CLOUDAMQP_URL,
                backend=CLOUDAMQP_URL,
                include=['tasks'])

# Optional configuration, see the application user guide.
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
    BROKER_POOL_LIMIT=1
)

if __name__ == '__main__':
    celery.start()