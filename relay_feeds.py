"""
Tornado Websockets and RethinkDB changefeeds handlers for Relay
"""

import logging
from tornado.websocket import WebSocketHandler
from tornado.gen import coroutine
import rethinkdb as r
from tornado.ioloop import IOLoop
import json


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
        logging.debug('WebSocketHandler on_close')
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


inventory_clients = []

class InventoryWSHandler(WebSocketHandler):
    def initialize(self, db):
        self.db = db

    @coroutine
    def open(self):
        logging.debug('InventoryWSHandler open')
        self.stream.set_nodelay(True)
        if self not in inventory_clients:
            inventory_clients.append(self)

    @coroutine
    def on_message(self, message):
        inventory = json.loads(message)
        self.db.add_to_inventory(inventory)

    @coroutine
    def on_close(self):
        logging.debug('InventoryWSHandler on_close')
        for i, client in enumerate(inventory_clients):
            if client is self:
                del inventory_clients[i]
                return

    def check_origin(self, origin):
        # Unrestricted access for now
        return True

@coroutine
def notice_inventory_changes(db):
    logging.debug('start inventory change')
    feed = yield r.table('inventory').changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        for client in inventory_clients:
            if change.get('new_val') is not None:
                logging.debug('one inventory change %s ' % change)
                client.write_message(change['new_val']['id'])
