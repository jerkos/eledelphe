#from __future__ import absolute_import
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

import logging
import os

from mongoengine import connect

#from utils import merge
from feature import Peakel
from model import MetabolomicsExperiment, Abundance, Annotation, Feature
#from mongo_db import MetabolomicsExperiment, Feature, Annotation, Abundance


class ResultsExporter(object):
    """
    Exports the result in a tsv file
    """
    HMDB, KEGG = "HMDB_ID=", "KEGG_ID="

    HEADER = "id\tmz\ttime\tMain putative tag\t" \
             "Main tag pattern composition\tPutative secondary attributions\t" \
             "Putative annotation\tPutative formula\tinChi\tDatabaseID\tIsotopic pattern matching score\t" \
             "Annotation assignment probability\tAnnotation pattern composition\n"

    def __init__(self, output, features):
        self.output_filepath = output
        self.peakels = features
        self.peakels_by_id = {p.id: p for p in self.peakels}

    @staticmethod
    def _get_main_putative_attribution(feature):
        """

        @param feature:
        @return:
        """
        main_put_attribution = ""
        if feature.main_attribution is None:
            s, n_isos, n_adds = feature.get_top_down_attribution_tree()

            # we got a possible monoisotopic
            if n_isos or n_adds:
                main_put_attribution += "monoisotope + "
                if n_isos:
                    main_put_attribution += "{} isotope(s)".format(n_isos)
                if n_adds:
                    if n_isos:
                        main_put_attribution += "+"
                    main_put_attribution += "{} adduct(s)/fragment(s)".format(n_adds)
        else:
            # we have iso || frag || adducts
            main_put_attribution = feature.main_attribution.attribution
        return main_put_attribution

    def _get_main_attribution_pattern_composition(self, feature):
        """

        @param feature:
        @return:
        """
        main_attribution_pattern_composition = ""
        if feature.main_attribution is None:
            m, q, s = feature.get_top_down_attribution_tree()
            main_attribution_pattern_composition += m
        else:
            main_attribution_pattern_composition += feature.get_bottom_up_attribution_tree(self.peakels_by_id)
        return main_attribution_pattern_composition

    def save_experiment(self, data):
        """
        Try to save results into MongoDB
        :param metabolites_by_feature:
        :param data
        @return: None
        """
        logging.info("Saving experiment in mongo db...")

        mongo = os.environ.get('MONGOHQ_URL')
        if mongo is not None :
            connect('hola', host=mongo)
        else:
            connect('omicsservices')

        exp = MetabolomicsExperiment()
        #exp.parameters = "All the xcms file goes here"
        exp.organization = data.get('organization', "IMS")
        exp.description = data['description']  #get('description', '')
        exp.title = data.get('title', "Alzeihmer")
        exp.software = data.get('software', "XCMS")
        exp.version = data.get('version', "3.18")

        exp.save()

        for p in self.peakels:
            ft = Feature()
            if p.main_attribution is not None:
                ft.main_attribution = p.main_attribution.attribution
            else:
                ft.main_attribution = self._get_main_putative_attribution(p)

            for k, v in p.area_by_sample_name.items():
                ab = Abundance(sample=k, abundance=v)
                ft.abundances.append(ab)

            #ft.attributions = p.attributions

            for m in p.annotations:
                annot = Annotation()
                annot.annotation = m.metabolite.name
                annot.score1 = m.score_isos
                annot.score2 = m.score_network
                ft.annotations.append(annot)

            ft.mass = p.moz
            ft.rt = p.rt
            ft.experiment_id = exp
            ft.save()

        logging.info("Done.")

    def write(self):
        """
        @param metabolites_scored_by_feature:
        @param metabolites_scored_by_feature_bayes:
        @return:
        """
        with open(self.output_filepath, 'w') as f:

            f.write(self.HEADER)

            for index, feature in enumerate(self.peakels):
                main_put_attribution = ResultsExporter._get_main_putative_attribution(feature)

                main_attribution_pattern_composition = self._get_main_attribution_pattern_composition(feature)

                #isotopes to compute score
                isostopes_score = [(i, i.get_attributions_by(lambda x: x.parent_id)[feature.id][0].attribution)
                                   for i in feature.ip_score_isotopes if i is not feature]
                # ip_score_isotopes = ";".join([str(i.id) + "=" + str(i.main_attribution.tag)
                #                               for i in feature.ip_score_isotopes if i.main_attribution is not None
                #                               and i is not feature])

                ip_score_isotopes = ";".join([str(p.id) + "=" + str(attribution_str)
                                              for p, attribution_str in isostopes_score])

                all_possible_attribution = ";".join(
                    [Peakel.get_others_bottom_up_attribution_tree(a, self.peakels_by_id)
                     for a in feature.attributions if a != feature.main_attribution]
                )

                feature_header = str(feature.id) + "\t" + str(feature.moz) + "\t" + str(feature.rt) + "\t"
                feature_header += "{0}\t{1}\t{2}\t".format(main_put_attribution, main_attribution_pattern_composition,
                                                           all_possible_attribution)

                f.write(feature_header)
                feature_metabolites = [(a.for_adduct, a.metabolite, a.score_isos, a.score_network)
                                       for a in feature.annotations]

                for idx, (for_adduct, metabolite, score1, score2) in enumerate(feature_metabolites):
                    data = ";".join([ResultsExporter.HMDB + metabolite.hmdb_id,  #acession,
                                     ResultsExporter.KEGG + metabolite.kegg_id]).encode("utf-8")
                    data = data.replace("\t", "")

                    s = feature_header if idx > 0 else ""
                    s += "\t".join([
                                    ": ".join([for_adduct, metabolite.name.encode("utf-8")]),
                                    metabolite.formula.encode("utf-8"),
                                    metabolite.inchi.encode("utf-8"),

                                    data,

                                    str(score1).encode("utf-8"),
                                    str(score2).encode("utf-8"),

                                    ip_score_isotopes
                                    ])
                    if idx < len(feature_metabolites) - 1:
                        s += "\n"
                    f.write(s)
                f.write("\n")

            #save experiment in mongodb
            #self.save_experiment(metabolites_scored_by_feature)





