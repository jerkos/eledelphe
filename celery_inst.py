__author__ = 'Marc'


from celery import Celery

celery = Celery('eledelphe',
             broker='amqp://',
             backend='amqp://',
             include=['tasks'])

# Optional configuration, see the application user guide.
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600,
)

if __name__ =='__main__':
    celery.start()