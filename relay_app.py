"""
Main app - setup, signal handling and graceful shutdown
"""

import os
from signal import signal, SIGTERM, SIGINT
from functools import partial

from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado.httpserver import HTTPServer

from relay_db import RelayDB
from relay_rest import MainHandler, \
    RegisterHandler, RegisterSuccessHandler, \
    TagsHandler, TeamsHandler
from relay_feeds import LeaderboardWSHandler, notice_team_changes, notice_walker_changes
from tests.relay_config import Config

import logging
logging.basicConfig(
    name=__name__,
    filename='relay.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(module)s %(message)s'
)


def sig_handler(server, sig, frame):
    # Stopping the app is nice, but closing the DB cleanly is the main point
    logging.debug('caught signal %d' % sig)
    IOLoop.instance().stop()


def run_app():
    db = RelayDB()
    IOLoop.instance().run_sync(db.open)
    handler_args = dict(db=db)
    app_settings = {
        'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        'debug': True
    }
    app = Application([
        (r'/', MainHandler, handler_args),
        (r'/leaderboard_ws', LeaderboardWSHandler, handler_args),
        (r'/register', RegisterHandler, handler_args),
        (r'/register_success', RegisterSuccessHandler, handler_args),
        (r'/tags', TagsHandler, handler_args),
        (r'/teams', TeamsHandler, handler_args),
        (r'/(pure-min\.css)', StaticFileHandler, dict(path=app_settings['static_path'])),
    ], autoreload=True, **app_settings)
    cfg = Config()
    server = HTTPServer(app)
    server.listen(cfg.app_port)
    signal(SIGTERM, partial(sig_handler, server))
    signal(SIGINT, partial(sig_handler, server))
    IOLoop.current().add_callback(notice_team_changes, **handler_args)
    IOLoop.current().add_callback(notice_walker_changes, **handler_args)
    IOLoop.instance().start()
    IOLoop.instance().run_sync(db.close)  # Close the DB cleanly to avoid corruption


if __name__ == '__main__':
    logging.info('starting')
    run_app()
    logging.info('exiting')
