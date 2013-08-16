#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask.ext.script import Manager

from fablib import app, db, sessions, DocumentModel, UserModel


manager = Manager(app)

@manager.command
def syncdb():
    """Initializes the database."""
    db.create_all()

@manager.command
def clear():
    sessions.redis.flushdb()
    db.drop_all()

if __name__ == "__main__":
    manager.run()