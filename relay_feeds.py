"""
Tornado Websockets and RethinkDB changefeeds handlers for Relay
"""

import logging
from tornado.websocket import WebSocketHandler
from tornado.gen import coroutine
import rethinkdb as r
from tornado.ioloop import IOLoop
import json

from tests.relay_config import cfg

"""
Base class for Websockets bookkeeping
"""
class RelayWSHandler(WebSocketHandler):
    def initialize(self, db):
        self.db = db
        # per-instance access to global/static member data
        self.clients = self.get_clients()  

    @coroutine
    def open(self):
        self.stream.set_nodelay(True)
        if self not in self.clients:
            self.clients.append(self)

    @coroutine
    def on_close(self):
        for i, client in enumerate(self.clients):
            if client is self:
                del self.clients[i]
                return

    def check_origin(self, origin):
        return True  # Unrestricted access for now


"""
Supports dynamic lap counts for walkers and teams. 
Consumed by Spencer's Lap-Counter-Viewer JS app
"""
class LeaderboardWSHandler(RelayWSHandler):
    clients = []

    def get_clients(self):
        return LeaderboardWSHandler.clients

    @coroutine
    def on_message(self, message):
        tags = [int(t) for t in message.split(',')]
        self.db.increment_laps(tags)


@coroutine
def notice_team_changes(db):
    feed = yield r.table(cfg.team_table).order_by(index=r.desc('laps'))\
        .limit(15).changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in LeaderboardWSHandler.clients:
                client.write_message({'type': 'leaderboard', 'data': change})

@coroutine
def notice_walker_changes(db):
    feed = yield r.table(cfg.walker_table).with_fields('id', 'team_id', 'laps').changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in LeaderboardWSHandler.clients:
                client.write_message({'type': 'ticker', 'data': change})
