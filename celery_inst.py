__author__ = 'Marc'

import os
import logging
import time

from celery import Celery

from mzos.peaklist_reader import PeakListReader
from mzos.annotator import PeakelsAnnotator
from mzos.database_finder import DatabaseSearch
from mzos.stats import StatsModel
from mzos.exp_design import ExperimentalSettings
from mzos.exp_design import IONISATION_MODE
from mzos.bayesian_inference import BayesianInferer
from mzos.results_exporter import ResultsExporter


CLOUDAMQP_URL = os.environ.get('CLOUDAMQP_URL', 'amqp://')

celery = Celery('celery_inst',
                broker=CLOUDAMQP_URL + '?heartbeat=30',
                backend='amqp',
                include=['tasks'])

celery.BROKER_POOL_LIMIT = 1
celery.BROKER_CONNECTION_TIMEOUT = 10

# Optional configuration, see the application user guide.
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600
)

if __name__ == '__main__':
    celery.start()