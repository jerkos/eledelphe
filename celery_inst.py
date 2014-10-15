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
                backend='amqp')

celery.BROKER_POOL_LIMIT = 1
celery.BROKER_CONNECTION_TIMEOUT = 10

# Optional configuration, see the application user guide.
celery.conf.update(
    CELERY_TASK_RESULT_EXPIRES=3600
)


@celery.task
def annotate_and_save(filename, arguments):
    """
    data is a dict containing all parameters for launching an annotations
    @param data:
    @return:
    """

    if filename is None or not filename:
        raise ValueError("Supply a XCMS peaklist.")
    # if not os.path.isfile(filename):
    #     raise ValueError("XCMS peaklist path does not seem to be valid.")

    if arguments['polarity'] is None:
        raise ValueError("polarity must be '-1' or '+1.'")
    polarity = IONISATION_MODE.NEG if arguments['polarity'] == 'negative' else IONISATION_MODE.POS
    is_dims = True if arguments.get('is_dims') else False
    adducts = arguments.getlist('adds')
    exp_settings = ExperimentalSettings(float(arguments['mz_tol_ppm']), adducts, polarity, is_dims)

    #clear logging
    logging.getLogger('').handlers = []

    logging.basicConfig(level=logging.INFO)
    t1 = time.clock()

    peakels = PeakListReader(filename, exp_settings).get_peakels()
    logging.info("Peaklist loaded.")

    ##annotation##
    peakels_annotator = PeakelsAnnotator(peakels, exp_settings)
    logging.info("Annotating...")

    best_monos = peakels_annotator.annotate_()
    logging.info("Monoisotopic found: #{}".format(len(best_monos)))

    ##database finding##
    db_search = DatabaseSearch('hmdb', exp_settings)
    logging.info("Searching in database...")
    adducts_l = ['H1']
    nb_metabs, not_found = db_search.assign_formula(peakels, adducts_l, exp_settings.mz_tol_ppm)
    logging.info("Found #{} metabolites, #{} "
                 "elution peak with no metabolite assignments".format(nb_metabs, not_found))

    ##scoring
    #first simplistic
    model = StatsModel(peakels, exp_settings.mz_tol_ppm * 1.5)
    logging.info("Compute score 1....")
    #populate annotations objects
    model.calculate_score()
    logging.info("Done")

    ##scoring 2##
    bi = BayesianInferer(peakels, exp_settings)
    logging.info("Compute score 2...")
    #populate annotations object
    bi.infer_assignment_probabilities()
    logging.info("Finished")

    logging.info('Exporting results...')
    exporter = ResultsExporter('', peakels)
    exporter.save_experiment(arguments)

if __name__ == '__main__':
    celery.start()