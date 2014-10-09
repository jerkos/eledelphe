#from __future__ import absolute_import

import datetime
from math import ceil
import os
import os.path as op

from flask import Flask, render_template, redirect, url_for, request, session, flash, abort
#from flask.ext.pymongo import PyMongo
from mongoengine import Document, StringField, DateTimeField, Q
from flask.ext.mongoengine import MongoEngine, Pagination
from werkzeug import secure_filename
from werkzeug.routing import BaseConverter, ValidationError
from itsdangerous import base64_encode, base64_decode
from bson.objectid import ObjectId
from bson.errors import InvalidId

from model import MetabolomicsExperiment, Experiment, Feature
import tasks


class ObjectIDConverter(BaseConverter):
    """ Object"""

    def to_python(self, value):
        """
        """
        try:
            return ObjectId(base64_decode(value))
        except (InvalidId, ValueError, TypeError):
            raise ValidationError()
    def to_url(self, value):
        """
        """
        return base64_encode(value.binary)

app = Flask(__name__)
app.url_map.converters['objectid'] = ObjectIDConverter
app.name = "omicsservices"
app.config.update(SECRET_KEY='development key',
                  USERNAME='admin',
                  PASSWORD='default')

app.config['MONGODB_SETTINGS'] = {'db': 'omicsservices'}

if not op.exists('./uploads'):
    os.mkdir('./uploads')
app.config['UPLOAD_FOLDER'] = './uploads'

db = MongoEngine(app)


PER_PAGE = 5

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def hello():
    """
    :return:
    """
    error = None
    if request.method == 'POST':
        if request.form['username'] != app.config['USERNAME']:
            error = 'Invalid username'
        elif request.form['password'] != app.config['PASSWORD']:
            error = 'Invalid password'
        else:
            session['logged_in'] = True
            session['username'] = request.form['username']
            flash('You were successfully logged in', 'success')
            return redirect(url_for('hello_world'))
    return render_template('login.html', error=error)

@app.route('/logout', methods=['POST', 'GET'])
def goodbye():
    session.pop('logged_in', None)
    return redirect(url_for('hello'))


@app.route('/experiments/', defaults={'page': 1})
@app.route('/experiments/page/<int:page>', methods=['GET'])
def hello_world(page):
    """
    :return:
    """
    if not session.get('logged_in'):
        abort(401)
    paginator = Pagination(MetabolomicsExperiment.objects, page=page, per_page=PER_PAGE)
    return render_template("experiments.html",
                           experiments=paginator.items,
                           pagination=paginator,
                           login=session['username'])


@app.route('/experiment/<objectid:exp_id>', methods=['GET', 'POST'])
def show_experiment(exp_id):
    """ show experiment
    @param exp_id:
    """
    if request.method == 'GET':
        experiment = Experiment.objects(id=exp_id).first()
        flash('fetch experiment id {}'.format(exp_id))
        return render_template('experiment.html', experiment=experiment, login=session['username'])
    # deal the update post
    organization, description, software, version, parameters = request.form['organization'], \
                                                               request.form['description'], \
                                                               request.form['software'], \
                                                               request.form['version'], \
                                                               request.form['parameters']
    MetabolomicsExperiment.objects(id=exp_id).update(set__organization=organization, set__description=description,
                                         set__software=software, set__version=version, set__parameters=parameters)
    flash("experiment {} has been updated".format(exp_id), 'success')
    return redirect(url_for('hello_world'))

@app.route('/features/<objectid:exp_id>/<int:page>', methods=['GET'])
def features(exp_id, page=1):
    """

    :param experiment_id:
    :return:
    """
    name_met = request.args.get('search')
    experiment = Experiment.objects(id=exp_id).first()
    if name_met is None:
        print "search is none"
        features = Feature.objects(experiment_id=exp_id).order_by('mass')
    else:
        print "DEBUG search {}".format(name_met)
        features = Feature.objects(experiment_id=exp_id).filter(annotations__annotation__contains=name_met)
    paginator = Pagination(features, page=page, per_page=PER_PAGE)
    return render_template("features.html", experiment=experiment,
                           features=paginator.items, pagination=paginator, login=session['username'])



# @app.route('/update_experiment/<objectid:exp_id>', methods=)


@app.route('/save_experiment', methods=['POST'])
def save_experiment():
    """
    upload a file and save it using its experiment id
    @return:
    """
    print "hello"
    organization, title, date, \
    description, software, version = request.form['organization'], request.form['title'], \
                                     request.form['date'], request.form['description'], \
                                     request.form['software'], request.form['version']

    experiment = MetabolomicsExperiment(organization=organization, title=title, date=date)
    experiment.description = description
    experiment.software = software
    experiment.version = version
    experiment.save()
    print 'after save'
    file = request.files['parameters']
    print "file:", file
    if file:
        filename = secure_filename(str(experiment.id))
        file.save(op.join(app.config['UPLOAD_FOLDER'], filename))

    return "<h1>file has been uploaded</h1>"

# @app.route('/show_parameters/<objectid:experiment_id>')
# def show_parameters(experiment_id):
#     """
#     show script or parameters for an experiment
#     @param experiment_id:
#     @return:
#     """
#     experiment = MetabolomicExperiment.objects(id=experiment_id)
#     print str(experiment_id)
#     path = "".join(['./uploads/', str(experiment_id)])
#     if not op.exists(path):
#         return abort(404)
#     text = open(path).read()
#     return render_template('parameters.html', experiment=experiment, text=text)


@app.route('/save_experiment_form')
def save_experiment_form():
    """
    @return: template form to save experiment metadata
    """
    return render_template('save_experiment.html', login=session['username'])

@app.route('/show_jobs')
def show_jobs():
    """iframe to flower celery admin panel"""
    return render_template('flower.html',login=session['username'])


@app.route('/launch_exp', methods=['GET', 'POST'])
def launch_experiment():
    """
    @return:
    """
    if request.method == 'GET':
        flash('Fill this before')

        return render_template('launch_exp.html', login=session['username'])

    #handle post method
    # organization, title, date, \
    # description, software, version, parameters = request.form['organization'], request.form['title'], \
    #                                  request.form['date'], request.form['description'], \
    #                                  request.form['software'], request.form['version'], request['parameters']

    f = request.files['peaklist']
    print "file:", f
    if f:
        filename = secure_filename("".join(['pkl', str(datetime.datetime.now()), '.csv']))
        f.save(op.join(app.config['UPLOAD_FOLDER'], filename))
    else:
        raise WindowsError("Error")
    print request.form.getlist('adds')
    tasks.annotate_and_save.delay(op.join(app.config['UPLOAD_FOLDER'], filename), request.form)

    return redirect(url_for('hello_world'))


if __name__ == '__main__':
    app.run(debug=True)