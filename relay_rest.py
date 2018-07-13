"""
RESTful API handlers for Relay web pages
"""

import json
import logging
from tornado.gen import coroutine, Return
from tornado.web import RequestHandler
from datetime import datetime


def friendly_date(ts):
    if ts == 0:
        return ''
    else:
        return datetime.fromtimestamp(ts).strftime('%x %X')


# Base class for all our RequestHandlers to have access to the DB
class RelayHandler(RequestHandler):
    def initialize(self, db):
        self.db = db

    @coroutine
    def get_teams_by(self, sort_key, reverse=False):
        teams = yield self.db.get_teams()
        raise Return(sorted(teams, key=lambda t: t[sort_key], reverse=reverse))

    def get_selected_team(self, teams, team_id):
        selected_team = {}
        for team in teams:
            if team['id'] == team_id:
                selected_team = team
        return selected_team


class MainHandler(RelayHandler):
    def get(self):
        self.write('Hello, Relay World')


# Display a walker's statistics
class WalkerHandler(RelayHandler):
    @coroutine
    def get(self, tag_id_str):
        tag_id = int(tag_id_str)
        walker = yield self.db.get_walker(tag_id)
        teams = yield self.get_teams_by('name')
        self.render(
            'static/walker.html',
            title='Walker',
            teams=teams,
            walker=walker,
            selected_team=self.get_selected_team(teams, walker['team_id']),
            friendly_date=friendly_date
        )

    @coroutine
    def post(self, _):
        tag_param = self.get_body_argument('tags', '')
        team_param = self.get_body_argument('team_id', '')
        if tag_param and team_param:
            team_id = int(team_param)
            ids = []
            if '-' in tag_param:
                l = [int(t) for t in tag_param.split('-')]
                ids = range(min(l), max(l) + 1)
            elif ',' in tag_param:
                ids = [int(t) for t in tag_param.split(',')]
            else:
                ids = [int(tag_param)]
            walkers = []
            for i in ids:
                walkers.append(dict(id=i, team_id=team_id))
            self.db.insert_walkers(walkers)
            self.redirect('/team/%d' % team_id)
        else: 
            self.set_status(400)
            self.finish()


# Add tags/walkers to the DB, or get registered tags
class TagsHandler(RelayHandler):
    @coroutine
    def get(self):
        # Used by populate.py test script to simulate tag reads
        tags = yield self.db.get_tags()
        self.write(json.dumps(tags))
        self.finish()

    @coroutine
    def post(self):
        walkers = json.loads(self.request.body)
        self.db.insert_walkers(walkers)


# Add one team, or display one team's statistics
class TeamHandler(RelayHandler):
    @coroutine
    def get(self, team_id_str):
        team_id = int(team_id_str)
        walkers = yield self.db.get_walkers(team_id)
        teams = yield self.get_teams_by('name')

        self.render(
            'static/team.html',
            title='Team',
            teams=teams,
            selected_team=self.get_selected_team(teams, team_id),
            walkers=sorted(walkers, key=lambda w: w['id']),
            friendly_date=friendly_date
        )

    @coroutine
    def post(self, _):
        team_name = self.get_body_argument('team_name', default='')
        if team_name:
            self.db.insert_teams([{'name':team_name}])
            self.redirect('/teams/')


# Add multiple teams, or display all teams' statistics
class TeamsHandler(RelayHandler):
    @coroutine
    def get(self):
        teams = yield self.get_teams_by('name')
        teams_by_laps = yield self.get_teams_by('laps', True)
        self.render(
            'static/teams.html',
            title='Teams',
            teams=teams,
            teams_by_laps=teams_by_laps,
            selected_team=None,
            total_laps = sum(t['laps'] for t in teams)
        )

    @coroutine
    def post(self):
        teams = json.loads(self.request.body)
        self.db.insert_teams(teams)
        self.finish()


class ZeroHandler(RelayHandler):
    @coroutine
    def get(self):
        raise NotImplementedError

    @coroutine
    def post(self):
        self.db.zero_all_laps()
        self.redirect('/teams/')
