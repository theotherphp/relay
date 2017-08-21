"""
Tornado Websockets and RethinkDB changefeeds handlers for Relay
"""

import logging
from tornado.websocket import WebSocketHandler
from tornado.gen import coroutine

import rethinkdb as r
import json


clients = []

class LeaderboardWSHandler(WebSocketHandler):
    def open(self):
        logging.debug('WebSocket opened')
        self.stream.set_nodelay(True)
        if self not in clients:
            clients.append(self)
        logging.debug('number of clients: %d' % len(clients))

    @coroutine
    def on_message(self, message):
        logging.warn('unexpected on_message %s' % message)

    def on_close(self):
        logging.debug('WebSocket closed')
        for i, client in enumerate(clients):
            if client is self:
                del clients[i]
                return

    def check_origin(self, origin):
        # Unrestricted access for now
        logging.warn("Trusting connection from "+str(origin))
        return True

@coroutine
def print_leaderboard_changes():
    r.set_loop_type('tornado')
    conn = yield r.connect(db='relay', port=28015)
    feed = yield r.table('teams').order_by(index=r.desc('laps')).limit(10).changes().run(conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            logging.debug('leaderboard change: %s' % change)
            for client in clients:
                client.write_message({'type': 'leaderboard', 'data': change})

@coroutine
def print_ticker_changes():
    r.set_loop_type('tornado')
    conn = yield r.connect(db='relay', port=28015)
    feed = yield r.table('walkers').changes().run(conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            logging.debug('ticker change: %s' % change)
            for client in clients:
                client.write_message({'type': 'ticker', 'data': change})
