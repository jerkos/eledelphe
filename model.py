__email__ = 'marc.dubois@omics-services.com'

from pymongo.connection import Connection
from mongoengine import EmbeddedDocument, FloatField, StringField, Document, \
    IntField, ListField, EmbeddedDocumentField, ReferenceField, DateTimeField
from datetime import datetime


class Experiment(Document):
    """
    Base class for various experiments
    """
    experiment_type_id = StringField(default="Not specified")
    organization = StringField(required=True)
    title = StringField(required=True)
    description = StringField(required=True)
    date = DateTimeField(required=False, default=datetime.now())

    meta = {'collection': 'experiments',
            'allow_inheritance': True}


class MetabolomicsExperiment(Experiment):
    """
    Metabolomics experiments
    """
    experiment_type_id = StringField(default="metabolomics")

    software = StringField(required=True)
    version = StringField(required=True)
    parameters = StringField()
    filenames = ListField(StringField())


class Annotation(EmbeddedDocument):
    """
    metabolite name with its 2 scores
    """
    annotation = StringField()
    score1 = FloatField()
    score2 = FloatField()


class Abundance(EmbeddedDocument):
    """
    Custom abundances class
    """
    sample = StringField()
    abundance = FloatField()


class Feature(Document):
    """
    Feature class
    """
    experiment_id = ReferenceField(Experiment)
    mass = FloatField(required=True)
    rt = FloatField(required=True)
    abundances = ListField(EmbeddedDocumentField(Abundance))
    main_attribution = StringField()
    annotations = ListField(EmbeddedDocumentField(Annotation))

    meta = {'collection': 'features'}


