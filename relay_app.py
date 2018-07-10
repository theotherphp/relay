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
from relay_rest import MainHandler, TagsHandler, TeamHandler, TeamsHandler, \
WalkerHandler, ZeroHandler
from relay_feeds import LeaderboardWSHandler, LapsWSHandler

from relay_config import cfg

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
        'pure_path': os.path.join(os.path.dirname(__file__), 'static', 'pure'),
        'viewer_path': os.path.join(os.path.dirname(__file__), 'static', 'Lap-Counter-Viewer'),
        'debug': True
    }
    app = Application([
        # Leaderboard support
        (r'/(index.*\.html)', StaticFileHandler, dict(path=app_settings['viewer_path'])),
        (r'/(css/index.*\.css)', StaticFileHandler, dict(path=app_settings['viewer_path'])),
        (r'/(js/(.*)\.js)', StaticFileHandler, dict(path=app_settings['viewer_path'])),
        (r'/(.*\.mp3)', StaticFileHandler, dict(path=app_settings['static_path'])),
        (r'/', MainHandler, handler_args),
        (r'/leaderboard_ws', LeaderboardWSHandler, handler_args),        
        (r'/laps_ws', LapsWSHandler, handler_args),        
        (r'/tags', TagsHandler, handler_args),
        # Admin web pages using https://purecss.io
        (r'/(pure-min\.css)', StaticFileHandler, dict(path=app_settings['pure_path'])),
        (r'/(side-menu\.css)', StaticFileHandler, dict(path=app_settings['pure_path'])),
        (r'/(ui\.js)', StaticFileHandler, dict(path=app_settings['pure_path'])),
        (r'/teams/', TeamsHandler, handler_args),
        (r'/team/(.*)', TeamHandler, handler_args),
        (r'/walker/(.*)', WalkerHandler, handler_args),
        (r'/zero/', ZeroHandler, handler_args)
    ], autoreload=True, **app_settings)
    server = HTTPServer(app)
    server.listen(cfg.app_port)
    signal(SIGTERM, partial(sig_handler, server))
    signal(SIGINT, partial(sig_handler, server))
    IOLoop.current().start()
    IOLoop.current().run_sync(db.close)  # Close the DB cleanly to avoid corruption


if __name__ == '__main__':
    logging.info('starting')
    run_app()
    logging.info('exiting')
