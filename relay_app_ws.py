"""
Main app - setup, signal handling and graceful shutdown
"""

import os
import rethinkdb as r
from tornado.ioloop import IOLoop
from tornado.web import Application, StaticFileHandler
from tornado.httpserver import HTTPServer

from relay_db import RelayDB
from relay_rest import MainHandler, RegisterHandler, RegisterSuccessHandler,\
    TeamsHandler
from relay_feeds import LeaderboardWSHandler, print_leaderboard_changes, print_ticker_changes

import logging
logging.basicConfig(
    name=__name__,
    filename='relay_ws.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(module)s %(message)s'
)

def run_app():
    r.set_loop_type('tornado')
    app_settings = {
        'static_path': os.path.join(os.path.dirname(__file__), 'static'),
        'debug': True
    }
    app = Application([
        (r'/leaderboard_ws', LeaderboardWSHandler),
        (r'/(leaderboard_ws\.html)', StaticFileHandler, dict(path=app_settings['static_path'])),
    ], autoreload=True)
    server = HTTPServer(app)
    server.listen(8889)
    IOLoop.current().add_callback(print_leaderboard_changes)
    IOLoop.current().add_callback(print_ticker_changes)
    IOLoop.instance().start()


if __name__ == '__main__':
    logging.info('starting')
    run_app()
    logging.info('exiting')
