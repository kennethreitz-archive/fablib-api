# -*- coding: utf-8 -*-

import os
import hashlib

import boto
from flask import Flask, request, abort, redirect
from flask.ext.restful import Resource, Api, reqparse
from markdown import markdown

BUCKET_NAME = os.environ['BUCKET_NAME']
DATABASE_URL = os.environ['DATABASE_URL']

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

app = Flask(__name__)
app.debug=True
api = Api(app)
trunk = Trunk(BUCKET_NAME)

@app.route('/')
def hello():
    return 'Hello World!'

todos = {}
todos['1'] = 'yo'


_user = {
    'name': 'kennethreitz',
    'email': 'me@kennethreitz.com',
    'password': 'xxxxx'
}

_document = {
    'name': 'kennethreitz',
    'slug': 'emulators',
    'text': '# Emulators\n\nGames are fun.',
    'owner': 'kennethreitz'
}



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
        return {'user': _user, 'document': _document}

    def put(self, profile, document):
        todos[profile] = request.form['data']
        return {'user': _user, 'document': _document}

class Content(Resource):
    def get(self, key):
        return {'text': trunk.get(key)}

    # def put(self, key, data):
    #     todos[profile] = request.form['data']
    #     return {'user': _user, 'document': _document}

api.add_resource(Content, '/content/<string:key>')


class NewContent(Resource):
    def post(self):
        data = request.form['text']
        key = trunk.store(data)
        return {'success': True, 'id': key}, 301, {'Location': '/content/{}'.format(key)}

    def put(self):
        return self.post()

api.add_resource(NewContent, '/content')


@app.route('/render', methods=['PUT', 'POST'])
def render():
    pass

@app.route('/render/<string:profile>/<path:document>')
def render_document(profile, document):

    return markdown(_document['text'])

class MarkdownService(Resource):
    def get(self, profile, document):
        return {'user': _user, 'document': _document}

    def put(self, profile, document):
        todos[profile] = request.form['data']
        return {'user': _user, 'document': _document}

api.add_resource(MarkdownService, '/render')




if __name__ == '__main__':
    app.run()