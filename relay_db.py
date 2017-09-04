import logging
import rethinkdb as r
from datetime import datetime as dt
import time
from tornado.gen import coroutine, Return

from tests.relay_config import Config

cfg = Config()
DB_NAME = cfg.db_name
WALKER_TABLE = 'walkers'
TEAM_TABLE = 'teams'
INVENTORY_TABLE = 'inventory'
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
            yield r.db(DB_NAME).table_create(WALKER_TABLE, durability='soft').run(self.conn)
            yield r.table(WALKER_TABLE).index_create('laps').run(self.conn)
            yield r.table(WALKER_TABLE).index_create('name').run(self.conn)
            yield r.table(WALKER_TABLE).index_create('team_id').run(self.conn)
            yield r.table(WALKER_TABLE).index_create('wristband').run(self.conn)
            yield r.table(WALKER_TABLE).index_wait().run(self.conn)
            yield r.db(DB_NAME).table_create(TEAM_TABLE, durability='soft').run(self.conn)
            yield r.table(TEAM_TABLE).index_create('laps').run(self.conn)
            yield r.table(TEAM_TABLE).index_wait().run(self.conn)
            yield r.db(DB_NAME).table_create(INVENTORY_TABLE, durability='soft').run(self.conn)
            yield r.table(INVENTORY_TABLE).index_create('reader_id').run(self.conn)
            yield r.table(INVENTORY_TABLE).index_wait().run(self.conn)


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
    def insert_walker(self, walker):
        cur = yield r.table(WALKER_TABLE).get_all(walker['wristband'], index='wristband').run(self.conn)
        length = 0
        while (yield cur.fetch_next()):
            item = yield cur.next()
            length = length + 1
        if length > 0:
            logging.warn('wristband %s already in use %d times' % (walker['wristband'], len(cur)))

        cur = yield r.table(WALKER_TABLE).get_all(walker['name'], index='name').run(self.conn)
        while (yield cur.fetch_next()):
            db_walker = yield cur.next()
            if walker['team_id'] == db_walker['team_id']:  # permit same name across teams
                logging.warn('name is already assigned to wristband %s', db_walker['wristband'])

        result = yield r.table(WALKER_TABLE).insert(walker).run(self.conn)
        if result is None or result.get('errors') != 0:
            logging.error('add_walker %s' % result)


    @coroutine
    def get_tag_id_by_wristband(self, wristband):
        # TODO
        raise NotImplementedError


    @coroutine 
    def increment_laps(self, tags):
        DEDUPLICATION_THRESHOLD = 2.0

        now = time.time()
        # Get the walkers matching these tags
        cur = yield r.table(WALKER_TABLE).get_all(r.args(tags))\
            .filter(r.row['last_updated_time'] < now - DEDUPLICATION_THRESHOLD).run(self.conn)
        id_list = []
        team_list = []
        while (yield cur.fetch_next()):
            walker = yield cur.next()
            id_list.append(walker['id'])
            team_list.append(walker['team_id'])
        # Update lap counts for non-duplicate walkers
        # Duplicates could be multiple reads of the same tag, or someone trying to cheat
        changes = yield r.table(WALKER_TABLE).get_all(r.args(id_list)).update({
            'laps': r.row['laps'] + 1,
            'last_updated_time': now
        }).run(self.conn)
        # Update lap counts for walkers' teams
        yield r.table(TEAM_TABLE).get_all(r.args(team_list)).update({
            'laps': r.row['laps'] + 1
        }).run(self.conn)


    @coroutine
    def add_to_inventory(self, inventory):
        for t in inventory['tag_ids']:
            cur = yield r.table(INVENTORY_TABLE).get_all(t).run(self.conn)
            length = 0
            while (yield cur.fetch_next()):
                item = yield cur.next()
                length += 1
            if length > 0:
                logging.warn('tag_id %s already in inventory' % t)
            else:
                tag_info = dict(
                    id=t,
                    reader_id=inventory['reader_id'],
                    last_updated_time=time.time()
                )
                result = yield r.table(INVENTORY_TABLE).insert(tag_info).run(self.conn)
                if result is None or result.get('errors') != 0:
                    logging.error('add_to_inventory %s' % result)
