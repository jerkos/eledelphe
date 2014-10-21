__author__ = 'Marc'


# Copyright (C) 2014  omics-services.com
#
#     This program is free software: you can redistribute it and/or modify
#     it under the terms of the GNU General Public License as published by
#     the Free Software Foundation, either version 3 of the License, or
#     (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program.  If not, see <http://www.gnu.org/licenses/>.

__email__ = 'marc.dubois@omics-services.com'

import sys
import os
import logging
import time

from mzos.peaklist_reader import PeakListReader
from mzos.annotator import PeakelsAnnotator
from mzos.database_finder import DatabaseSearch
from mzos.stats import StatsModel
from mzos.exp_design import ExperimentalSettings
from mzos.exp_design import IONISATION_MODE
from mzos.bayesian_inference import BayesianInferer
from mzos.results_exporter import ResultsExporter

from celery_inst import celery

#@celery.task

@celery.task(bind=True)
def annotate_and_save(self, filename, arguments):
    """
    data is a dict containing all parameters for launching an annotations
    @param data:
    @return:
    """
    # Empty kwargs

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
    self.update_state(state='PROGRESS', meta={'current': 1, 'total': 6})

    ##annotation##
    peakels_annotator = PeakelsAnnotator(peakels, exp_settings)
    logging.info("Annotating...")

    best_monos = peakels_annotator.annotate_()
    logging.info("Monoisotopic found: #{}".format(len(best_monos)))
    self.update_state(state='PROGRESS', meta={'current': 2, 'total': 6})

    ##database finding##
    db_search = DatabaseSearch('hmdb', exp_settings)
    logging.info("Searching in database...")
    adducts_l = ['H1']
    nb_metabs, not_found = db_search.assign_formula(peakels, adducts_l, exp_settings.mz_tol_ppm)
    logging.info("Found #{} metabolites, #{} "
                 "elution peak with no metabolite assignments".format(nb_metabs, not_found))
    self.update_state(state='PROGRESS', meta={'current': 3, 'total': 6})


    ##scoring
    #first simplistic
    model = StatsModel(peakels, exp_settings.mz_tol_ppm * 1.5)
    logging.info("Compute score 1....")
    #populate annotations objects
    model.calculate_score()
    logging.info("Done")
    self.update_state(state='PROGRESS', meta={'current': 4, 'total': 6})


    ##scoring 2##
    bi = BayesianInferer(peakels, exp_settings)
    logging.info("Compute score 2...")
    #populate annotations object
    bi.infer_assignment_probabilities()
    logging.info("Finished")
    self.update_state(state='PROGRESS', meta={'current': 5, 'total': 6})


    logging.info('Exporting results...')
    exporter = ResultsExporter('', peakels)
    exporter.save_experiment(arguments)
    self.update_state(state='PROGRESS', meta={'current': 6, 'total': 6})

