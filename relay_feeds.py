"""
Tornado Websockets and RethinkDB changefeeds handlers for Relay
"""

import logging
from tornado.websocket import WebSocketHandler
from tornado.gen import coroutine
import rethinkdb as r
import time


clients = []
DEDUPLICATION_THRESHOLD = 2.0

class LeaderboardWSHandler(WebSocketHandler):
    def __init__(self, *args, **kwargs):
        self.conn = None
        super(LeaderboardWSHandler, self).__init__(*args, **kwargs)

    @coroutine
    def open(self):
        self.stream.set_nodelay(True)
        if self not in clients:
            clients.append(self)
        if self.conn is None:
            self.conn = yield r.connect(db='relay')

    @coroutine
    def on_message(self, message):
        tags = message.split(',')
        now = time.time()
        # Get the walkers matching these tags
        if self.conn is None:
            logging.debug('how did this happen')
            self.conn = yield r.connect(db='relay')
        cur = yield r.table('walkers').get_all(r.args(tags)).filter(r.row['last_updated_time'] < now - DEDUPLICATION_THRESHOLD).run(self.conn)
        id_list = []
        team_list = []
        while (yield cur.fetch_next()):
            walker = yield cur.next()
            id_list.append(walker['id'])
            team_list.append(walker['team_id'])
        # Update lap counts for non-duplicate walkers
        # Duplicates could be multiple reads of the same tag, or someone trying to cheat
        yield r.table('walkers').get_all(r.args(id_list)).update({
            'laps': r.row['laps'] + 1,
            'last_updated_time': now
        }).run(self.conn)
        # Update lap counts for walkers' teams
        logging.debug('team list: %s' % team_list)
        yield r.table('teams').get_all(r.args(team_list)).update({
            'laps': r.row['laps'] + 1
        }).run(self.conn)

    def on_close(self):
        for i, client in enumerate(clients):
            if client is self:
                del clients[i]
                if len(clients) == 0:
                    self.conn.close()
                    self.conn = None
                return

    def check_origin(self, origin):
        # Unrestricted access for now
        return True

@coroutine
def print_leaderboard_changes():
    r.set_loop_type('tornado')
    conn = yield r.connect(db='relay')
    feed = yield r.table('teams').order_by(index=r.desc('laps')).limit(10).changes().run(conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in clients:
                client.write_message({'type': 'leaderboard', 'data': change})

@coroutine
def print_ticker_changes():
    r.set_loop_type('tornado')
    conn = yield r.connect(db='relay')
    feed = yield r.table('walkers').changes().run(conn)
    while (yield feed.fetch_next()):
        change = yield feed.next()
        if change['new_val']['laps'] > 0:
            for client in clients:
                client.write_message({'type': 'ticker', 'data': change})
