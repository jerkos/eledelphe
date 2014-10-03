import datetime
from math import ceil
import os
import os.path as op
from flask import Flask, render_template, redirect, url_for, request, session, flash, abort
#from flask.ext.pymongo import PyMongo
from mongoengine import Document, StringField, DateTimeField
from flask.ext.mongoengine import MongoEngine, Pagination
from werkzeug import secure_filename
from werkzeug.routing import BaseConverter, ValidationError
from itsdangerous import base64_encode, base64_decode
from bson.objectid import ObjectId
from bson.errors import InvalidId


class ObjectIDConverter(BaseConverter):
    def to_python(self, value):
        try:
            return ObjectId(base64_decode(value))
        except (InvalidId, ValueError, TypeError):
            raise ValidationError()
    def to_url(self, value):
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


class MetabolomicExperiment(Document):
    meta = {'collection': 'experiments'}

    organization = StringField(required=True)
    title = StringField(required=True)
    date = DateTimeField(default=datetime.datetime.now)
    description = StringField(required=False)
    software = StringField(required=False)
    version = StringField(required=False)


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
            flash('You were logged in !!!')
            return redirect(url_for('hello_world'))
    return render_template('login.html', error=error)

@app.route('/logout', methods=['POST'])
def goodbye():
    session.pop('logged_in', None)
    return redirect(url_for('hello'))


@app.route('/experiments/', defaults={'page': 1})
@app.route('/experiments/page/<int:page>')
def hello_world(page):
    """
    :return:
    """
    if not session.get('logged_in'):
        abort(401)

    paginator = Pagination(MetabolomicExperiment.objects, page=page, per_page=PER_PAGE)
    return render_template("experiments.html", experiments=paginator.items, pagination=paginator)

# @app.route('/experiment/<int:experiment_id>/<int:page>')
# def get_experiment(experiment_id, page=1):
#     """
#
#     :param experiment_id:
#     :return:
#     """
#     experiment = mongo.db.experiments.find_one({'experiment_id': experiment_id})
#     nb_features = mongo.db.features.find({'experiment_id': experiment_id}).count()
#     min_i, max_i = get_experiments_indexes_for_page(page)
#     cursor = mongo.db.features.find({'experiment_id': experiment_id}).skip(min_i - 1).limit(PER_PAGE)
#     pagination = Pagination(page, nb_features)
#     features = list(cursor)
#     return render_template("experiment.html", experiment=experiment, features=features, pagination=pagination)

@app.route('/save_experiment', methods=['POST'])
def save_experiment():
    print "hello"
    organization, title, date, \
    description, software, version = request.form['organization'], request.form['title'], \
                                     request.form['date'], request.form['description'], \
                                     request.form['software'], request.form['version']

    experiment = MetabolomicExperiment(organization=organization, title=title, date=date)
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

@app.route('/show_parameters/<objectid:experiment_id>')
def show_parameters(experiment_id):
    experiment = MetabolomicExperiment.objects(id = experiment_id)
    print str(experiment_id)
    path = "".join(['./uploads/', str(experiment_id)])
    if not op.exists(path):
        return abort(404)
    text = open(path).read()
    return render_template('parameters.html', experiment=experiment, text=text)


@app.route('/save_experiment_form')
def save_experiment_form():
    return render_template('save_experiment.html')

@app.route('/show_jobs')
def show_jobs():
    return render_template('flower.html')

if __name__ == '__main__':
    app.run(debug=True)