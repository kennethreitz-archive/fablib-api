# -*- coding: utf-8 -*-

import os
import hashlib
from uuid import uuid4


import boto
import redis
from markdown import markdown
from flask import Flask, request, abort, redirect
from flask.ext.restful import Resource, Api, reqparse, abort as rest_abort
from flask.ext.sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


BUCKET_NAME = os.environ['BUCKET_NAME']
DATABASE_URL = os.environ['DATABASE_URL']
REDIS_URL = os.environ['OPENREDIS_URL']

SESSION_LIFETIME = (30 * 24)

class Trunk(object):

    def __init__(self, bucket):
        s3 = boto.connect_s3()

        if bucket not in s3:
            self.bucket = boto.connect_s3().create_bucket(bucket)
        else:
            self.bucket = boto.connect_s3().get_bucket(bucket)

    def hash(self, data):
        return hashlib.sha1(data).hexdigest()

    def store(self, data):
        key_name = self.hash(data)
        key = self.bucket.new_key(key_name)
        key.set_contents_from_string(data)

        return key_name

    def get(self, key, render=False):
        text = self.bucket.get_key(key).read()

        if render:
            text = markdown(text)

        return text


class Sessions(object):
    _prefix = 'sessions:'

    def __init__(self, redis_url):
        self.redis = redis.from_url(redis_url)

    def _transpose(self, key):
        return ''.join((self._prefix, key))

    def get(self, key):
        return self.redis.get(self._transpose(key))

    def get_user(self, key):
        return UserModel.from_username(self.get(key))

    def set(self, key, value):
        # self.redis.setex(self._transpose(key), SESSION_LIFETIME, value)
        self.redis.set(self._transpose(key), value)

    def create(self, username):
        user = UserModel.from_username(username)
        key = self.uuid()

        self.set(key, user.username)

        return key

    def login(self, username, password):
        user = UserModel.from_username(username)
        is_valid_pass = user.check_password(password)

        if is_valid_pass:
            return self.create(username)

    def is_valid(self, username, session):
        s_user = self.get_user(session)
        return username == s_user.username

    @staticmethod
    def uuid():
        return str(uuid4())

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.debug = True
api = Api(app)
db = SQLAlchemy(app)
trunk = Trunk(BUCKET_NAME)
sessions = Sessions(REDIS_URL)

@app.route('/')
def hello():
    return 'Hello World!'

todos = {}
todos['1'] = 'yo'


class BaseModel(object):
    def save(self):
        db.session.add(self)
        return db.session.commit()

class UserModel(db.Model, BaseModel):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    username = db.Column(db.String(80), unique=True)
    password = db.Column(db.String(120), unique=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    def __repr__(self):
        return '<User %r>' % self.username

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

    @staticmethod
    def from_username(username):
        return UserModel.query.filter_by(username=username).first()

class DocumentModel(db.Model, BaseModel):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(120))
    content = db.Column(db.String(80), unique=False)
    private = db.Column(db.Boolean, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    fork_of = db.Column(db.Integer, db.ForeignKey('documents.id'))

    def __repr__(self):
        return '<Document %r>' % self.id

    @property
    def forks(self):
        return DocumentModel.query.filter_by(fork_of=self).all()

    def set_content(self, data):
        key = trunk.set(data)
        self.content = key

    @staticmethod
    def from_keys(username, slug):
        user = UserModel.from_username(username)
        return DocumentModel.query.filter_by(owner_id=user.id, slug=slug).first()


class UserProfile(Resource):
    def get(self, profile):
        return {'user': _user}

    def put(self, profile):
        parser.add_argument('data', type=str)
        args = parser.parse_args()

        todos[profile] = args['data']
        return {'user': _user}

api.add_resource(UserProfile, '/<string:profile>')


class Document(Resource):
    def get(self, profile, document):
        try:
            u = UserModel.from_username(profile)
            d = DocumentModel.from_keys(profile, document)

        except AttributeError:
            rest_abort(404)

        content = trunk.get(d.content)
        user = {'username': u.username, 'email': u.email}
        doc = {'text': content}

        return {'user': user, 'document': doc}

    def put(self, profile, document):
        todos[profile] = request.form['data']
        return {'user': _user, 'document': _document}

api.add_resource(Document, '/<string:profile>/<path:document>')


class Content(Resource):
    def get(self, key):
        return {'text': trunk.get(key)}

api.add_resource(Content, '/content/<string:key>')


class NewContent(Resource):
    def post(self):
        data = request.form['text']
        key = trunk.store(data)
        return {'success': True, 'id': key}, 301, {'Location': '/content/{}'.format(key)}

    def put(self):
        return self.post()

api.add_resource(NewContent, '/content')

print redis

class SessionAPI(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, required=True)
        parser.add_argument('password', type=str, required=True)
        args = parser.parse_args()

        key = sessions.login(args.get('username'), args.get('password'))
        return {'success': True, 'session': key}, 301, {'Location': '/sessions/{}'.format(key)}

api.add_resource(SessionAPI, '/sessions')


class ActiveSessionAPI(Resource):
    def get(self, session):
        u = sessions.get_user(session)
        return {'valid': True, 'username': u.username, 'email': u.email, 'id': session}

api.add_resource(ActiveSessionAPI, '/sessions/<string:session>')


if __name__ == '__main__':
    app.run()