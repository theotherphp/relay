"""
RESTful API handlers for Relay web pages
"""

from tornado.web import RequestHandler
from tornado.gen import coroutine
from urlparse import parse_qsl
import json
import logging


# Base class for all our RequestHandlers to have access to the DB
class RelayHandler(RequestHandler):
    def initialize(self, db):
        self.db = db


class MainHandler(RelayHandler):
    def get(self):
        self.write('Hello, Relay World')


class RegisterHandler(RelayHandler):
    # Provide the registration page for one walker
    @coroutine
    def get(self):
        teams = yield self.db.get_teams()
        # self.render(
        #     'static/register.html',
        #     title='Register for Relay',
        #     teams=teams
        # )
        self.render(
            'static/register_ws.html',
            # title='Register for Relay',
            # teams=teams
        )

    # Add walker(s) to the DB so we can count their laps
    def post(self):
        walker = dict(parse_qsl(self.request.body))
        self._init_walker(walker)
        self.db.insert_walker(walker)
        self.redirect('/register_success')

    def _init_walker(self, walker):
        walker['laps'] = 0
        walker['last_updated_time'] = 0.0
        walker['wristband'] = int(walker['wristband'])
        walker['team_id'] = int(walker['team_id'])
        # TODO walker['id'] = self.db.get_tag_id_by_wristband(walker['wristband'])


class RegisterSuccessHandler(RelayHandler):
    def get(self):
        self.render(
            'static/register_success.html',
            title='Success'
        )


class TagsHandler(RelayHandler):
    @coroutine
    def get(self):
        # Used by populate.py test script to simulate tag reads
        tags = yield self.db.get_tags()
        self.write(json.dumps(tags))
        self.finish()

    def post(self):
        # Maybe this is how to do inventory of tags on hand?
        raise NotImplementedError


class TeamsHandler(RelayHandler):
    def get(self):
        self.render(
            'static/teams.html',
            title='Import Teams'
        )

    def post(self):
        teams = json.loads(self.request.body)
        self._init_teams(teams)
        self.db.insert_teams(teams)
        self.finish()

    def _init_teams(self, teams):
        for i in range(0, len(teams)):
            teams[i]['laps'] = 0
            teams[i]['id'] = i  # generated keys are so ugly
