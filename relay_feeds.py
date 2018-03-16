"""
Tornado Websockets and RethinkDB changefeeds handlers for Relay
"""

import logging
from tornado.websocket import WebSocketHandler
from tornado.gen import coroutine
import rethinkdb as r
from tornado.ioloop import IOLoop
import json

from relay_config import cfg

"""
Base class for Websockets bookkeeping
"""
class RelayWSHandler(WebSocketHandler):
    def initialize(self, db):
        self.alive = True
        self.db = db

    @coroutine
    def open(self):
        self.stream.set_nodelay(True)

    @coroutine
    def on_close(self):
        logging.debug('on_close')
        self.alive = False


"""
Supports dynamic lap counts for walkers and teams. 
Consumed by Spencer's Lap-Counter-Viewer JS app
"""
class LeaderboardWSHandler(RelayWSHandler):

    @coroutine
    def open(self):
        super(LeaderboardWSHandler, self).open()
        IOLoop.current().add_callback(self.notice_team_changes)
        IOLoop.current().add_callback(self.notice_walker_changes)

    @coroutine
    def notice_team_changes(self):
        feed = yield r.table(cfg.team_table).order_by(index=r.desc('laps'))\
            .limit(15).changes(include_initial=True).run(self.db.conn)
        while (yield feed.fetch_next()):
            change = yield feed.next()
            if self.alive:
                self.write_message({'type': 'leaderboard', 'data': change})
            else:
                logging.debug('notice_team_changes returning')
                return

    @coroutine
    def notice_walker_changes(self):
        feed = yield r.table(cfg.walker_table).without('lap_times')\
            .changes(include_initial=True).run(self.db.conn)
        while (yield feed.fetch_next()):
            change = yield feed.next()
            if change['new_val']['laps'] > 0:
                if self.alive:
                    self.write_message({'type': 'ticker', 'data': change})
                else:
                    logging.debug('notice_walker_changes returning')
                    return

class LapsWSHandler(RelayWSHandler):
    
    @coroutine
    def on_message(self, message):
        tags = [int(t) for t in message.split(',')]
        self.db.increment_laps(tags)

