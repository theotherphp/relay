"""
Tornado Websockets and RethinkDB changefeeds handlers for Relay
"""

import logging
from tornado.websocket import WebSocketHandler
from tornado.gen import coroutine
import rethinkdb as r
from tornado.ioloop import IOLoop


clients = []

class LeaderboardWSHandler(WebSocketHandler):
    def initialize(self, db):
        self.db = db

    @coroutine
    def open(self):
        self.stream.set_nodelay(True)
        if self not in clients:
            clients.append(self)

    @coroutine
    def on_message(self, message):
        tags = message.split(',')
        self.db.increment_laps(tags)

    @coroutine
    def on_close(self):
        for i, client in enumerate(clients):
            if client is self:
                del clients[i]
                return

    def check_origin(self, origin):
        # Unrestricted access for now
        return True


@coroutine
def notice_team_changes(db):
    feed = yield r.table('teams').order_by(index=r.desc('laps')).limit(10).changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in clients:
                client.write_message({'type': 'leaderboard', 'data': change})

@coroutine
def notice_walker_changes(db):
    feed = yield r.table('walkers').changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in clients:
                client.write_message({'type': 'ticker', 'data': change})
