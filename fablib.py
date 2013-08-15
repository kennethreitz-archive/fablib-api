# -*- coding: utf-8 -*-

from flask import Flask, request
from flask.ext.restful import Resource, Api

app = Flask(__name__)
api = Api(app)

@app.route('/')
def hello():
    return 'Hello World!'

todos = {}
todos['1'] = 'yo'

class UserProfile(Resource):
    def get(self, profile):
        return {profile: todos[profile]}

    def put(self, profile):
        todos[profile] = request.form['data']
        return {profile: todos[profile]}

api.add_resource(UserProfile, '/<string:profile>')

class Document(Resource):
    def get(self, profile, document):
        return {profile: todos[profile]}

    def put(self, profile, document):
        todos[profile] = request.form['data']
        return {profile: todos[profile]}

api.add_resource(Document, '/<string:profile>/<path:document>')




if __name__ == '__main__':
    app.run()