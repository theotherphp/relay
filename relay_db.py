import logging
import rethinkdb as r
from datetime import datetime as dt
import time
from tornado.gen import coroutine, Return

from tests.relay_config import cfg

DB_NAME = cfg.db_name
WALKER_TABLE = cfg.walker_table
TEAM_TABLE = cfg.team_table
MICROS_PER_SEC = 1000000.0
LAP_DEDUPLICATION_THRESHOLD = 2  # *60  # 2 minutes

class RelayDB(object):

    def __init__(self, *args, **kwargs):
        self.conn = None


    @coroutine
    def open(self):
        r.set_loop_type('tornado')
        self.conn = yield r.connect(db=DB_NAME)
        db_names = yield r.db_list().run(self.conn)
        if DB_NAME not in db_names:
            logging.debug('creating database')
            yield r.db_create(DB_NAME).run(self.conn)
        table_names = yield r.table_list().run(self.conn)
        if WALKER_TABLE not in table_names:
            yield r.db(DB_NAME).table_create(WALKER_TABLE, durability='soft').run(self.conn)
            yield r.table(WALKER_TABLE).index_create('laps').run(self.conn)
            yield r.table(WALKER_TABLE).index_create('team_id').run(self.conn)
            yield r.table(WALKER_TABLE).index_wait().run(self.conn)
        if TEAM_TABLE not in table_names:
            yield r.db(DB_NAME).table_create(TEAM_TABLE, durability='soft').run(self.conn)
            yield r.table(TEAM_TABLE).index_create('laps').run(self.conn)
            yield r.table(TEAM_TABLE).index_wait().run(self.conn)


    @coroutine
    def close(self):
        then = dt.now()
        for table in [WALKER_TABLE, TEAM_TABLE]:
            result = yield r.table(table).sync().run(self.conn)
            if result is None or result.get('synced') != 1:
                log.error('sync %s failed' % table)
        self.conn.close()
        delta = dt.now() - then
        duration = delta.seconds + (delta.microseconds/MICROS_PER_SEC)
        logging.debug('closed in %f secs' % duration)

 
    @coroutine
    def insert_teams(self, teams):
        generated_keys = []
        result = yield r.table(TEAM_TABLE).insert(teams).run(self.conn)
        if result is None or result.get('errors') != 0:
            logging.error('insert_teams %s ' % result)


    @coroutine
    def get_teams(self):
        teams = []
        cur = yield r.table(TEAM_TABLE).run(self.conn)
        while (yield cur.fetch_next()):
            team = yield cur.next()
            teams.append(team)
        raise Return(teams)


    @coroutine
    def get_tags(self):
        tags = []
        cur = yield r.table(WALKER_TABLE).with_fields('id').run(self.conn)
        while (yield cur.fetch_next()):
            item = yield cur.next()
            tags.append(item['id'])
        raise Return(tags)


    @coroutine
    def insert_walkers(self, walkers):
        result = yield r.table(WALKER_TABLE).insert(walkers).run(self.conn)
        if result is None or result.get('errors') != 0:
            logging.error('insert_walkers %s' % result)


    @coroutine 
    def increment_laps(self, tags):
        MIN_LAP_TIME = 60.0  # seconds
        now = time.time()

        tag_set = set(tags)  # remove any duplicate tags
        cur = yield r.table(WALKER_TABLE).get_all(r.args(list(tag_set))).run(self.conn)

        while (yield cur.fetch_next()):
            walker = yield cur.next()
            tag_set.remove(walker['id'])  # remove the ones we've seen to find unassigned below
            if now - walker['last_updated_time'] > MIN_LAP_TIME:
                # Increment lap totals
                yield r.table(WALKER_TABLE).get(walker['id']).update({
                    'laps': r.row['laps'] + 1,
                    'last_updated_time': now
                }).run(self.conn)
                yield r.table(TEAM_TABLE).get(walker['team_id']).update({
                    'laps': r.row['laps'] + 1
                }).run(self.conn)
            else:
                # Not so fast buddy
                d = dt.fromtimestamp(walker['last_updated_time'])
                logging.warn('too soon: %d last lap: %s' % (walker['id'], d.strftime('%x %X')))
        if len(tag_set) > 0:
            # Shouldn't happen
            logging.warn('unassigned tags: %s' % str(tag_set))
