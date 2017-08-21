"""
RESTful API handlers for Relay web pages
"""

from tornado.web import RequestHandler
from urlparse import parse_qsl
import json


# Base class for all our RequestHandlers to have access to the DB
class RelayHandler(RequestHandler):
    def initialize(self, db):
        self.db = db


class MainHandler(RelayHandler):
    def get(self):
        self.write('Hello, Relay World')


class RegisterHandler(RelayHandler):
    # Provide the registration page for one walker
    def get(self):
        self.render(
            'static/register.html',
            title='Register for Relay',
            teams=self.db.get_teams()
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
        # TODO walker['id'] = self.db.get_tag_id_by_wristband(walker['wristband'])


class RegisterSuccessHandler(RelayHandler):
    def get(self):
        self.render(
            'static/register_success.html',
            title='Success'
        )


class LeaderboardHandler(RelayHandler):
    # Provide leaderboard page
    def get(self):
        self.render(
            'static/leaderboard.html',
            title='Leaderboard',
            walkers=self.db.get_walkers_by('laps', 25),
            teams=self.db.get_teams_by('laps', 10)
        )

    # Post laps walked to the DB
    def post(self):
        tags = self.get_body_argument('rfid_tags_read')
        if tags is None:
            logging.error('malformed post %s' % self.request.body)
            self.send_error(status_code=400, kwargs={'malformed': self.request.body})
        else:
            self.db.post_laps(tags.split(','))
            self.finish('OK')


class TeamsHandler(RelayHandler):
    def get(self):
        self.render(
            'static/teams.html',
            title='Import Teams'
        )

    def post(self):
        teams = json.loads(self.request.body)
        self._init_teams(teams)
        generated_keys = self.db.insert_teams(teams)
        self.finish(json.dumps(generated_keys))

    def _init_teams(self, teams):
        color_index = 0
        for t in teams:
            t['laps'] = 0
            t['css_class'] = 'team_' + str(color_index)
            color_index = color_index + 1
            if color_index > 31:  # hard-coded limit in team_colors.css
                logging.warn('wrapping CSS color index')
                color_index = 0
