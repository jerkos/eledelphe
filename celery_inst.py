__author__ = 'Marc'

import os

from celery import Celery

CLOUDAMQP_URL = os.environ.get('CLOUDAMQP_URL', 'amqp://')

celery = Celery('celery_inst',
                broker=CLOUDAMQP_URL,
                backend='amqp')

celery.BROKER_POOL_LIMIT = 1

# Optional configuration, see the application user guide.
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600
)

if __name__ == '__main__':
    celery.start()