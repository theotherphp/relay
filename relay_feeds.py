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
        tags = message.split(',')
        self.db.increment_laps(tags)


@coroutine
def notice_team_changes(db):
    feed = yield r.table(cfg.team_table).order_by(index=r.desc('laps'))\
        .limit(10).changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in LeaderboardWSHandler.clients:
                client.write_message({'type': 'leaderboard', 'data': change})

@coroutine
def notice_walker_changes(db):
    feed = yield r.table(cfg.walker_table).changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in LeaderboardWSHandler.clients:
                client.write_message({'type': 'ticker', 'data': change})


"""
Add tags into inventory. Could be used for:
1. Bulk-reading inventory of tags to assign them to walkers at file-import time
2. Assigning tags to walkers at the Relay event using a reader at the volunteer desk
The reason this is a websocket is to allow the RFID reader to read tags in the client
python world, but have the tags accessible to web pages. Maybe there's an easier way.
"""
class InventoryWSHandler(RelayWSHandler):
    clients = []

    def get_clients(self):
        return InventoryWSHandler.clients

    @coroutine
    def on_message(self, message):
        inventory = json.loads(message)
        self.db.add_to_inventory(inventory)


@coroutine
def notice_inventory_changes(db):
    feed = yield r.table(cfg.inventory_table).changes().run(db.conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        for client in InventoryWSHandler.clients:
            if change.get('new_val') is not None:
                client.write_message(change['new_val']['id'])
