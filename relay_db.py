import logging
import rethinkdb as r
from datetime import datetime as dt
import time

DB_NAME = 'relay'
WALKER_TABLE = 'walkers'
TEAM_TABLE = 'teams'
MICROS_PER_SEC = 1000000.0
LAP_DEDUPLICATION_THRESHOLD = 2  # *60  # 2 minutes


class RelayDB(object):
    def __init__(self):
        self.team_id_map = None


    def open(self):
        self.conn = r.connect(db=DB_NAME, port=28015).repl()
        if DB_NAME not in r.db_list().run():
            logging.debug('creating database')
            r.db_create(DB_NAME).run()
            r.db(DB_NAME).table_create(WALKER_TABLE, durability='soft').run()
            r.table(WALKER_TABLE).index_create('laps').run()
            r.table(WALKER_TABLE).index_create('name').run()
            r.table(WALKER_TABLE).index_create('team_id').run()
            r.table(WALKER_TABLE).index_create('wristband').run()
            r.db(DB_NAME).table_create(TEAM_TABLE, durability='soft').run()
            r.table(TEAM_TABLE).index_create('laps').run()


    def close(self):
        then = dt.now()
        for table in [WALKER_TABLE, TEAM_TABLE]:
            result = r.table(table).sync().run()
            if result is None or result.get('synced') != 1:
                log.error('sync %s failed' % table)
        self.conn.close()
        delta = dt.now() - then
        duration = delta.seconds + (delta.microseconds/MICROS_PER_SEC)
        logging.debug('closed in %f secs' % duration)

 
    def insert_teams(self, teams):
        generated_keys = []
        result = r.table(TEAM_TABLE).insert(teams).run()
        if result is None or result.get('errors') != 0:
            logging.error('insert_teams %s ' % result)


    def get_teams(self):
        return r.table(TEAM_TABLE).run()


    def insert_walker(self, walker):
        cur = list(
            r.table(WALKER_TABLE)
            .get_all(walker['wristband'], index='wristband')
            .run()
        )
        if len(cur) > 0:
            logging.warn('wristband %s already in use %d times' % (walker['wristband'], len(cur)))

        cur = list(
            r.table(WALKER_TABLE).get_all(walker['name'], index='name').run()
        )
        for db_walker in cur:
            if walker['team_id'] == db_walker['team_id']:  # permit same name across teams
                logging.warn('name is already assigned to wristband %s', db_walker['wristband'])

        result = r.table(WALKER_TABLE).insert(walker).run()
        if result is None or result.get('errors') != 0:
            logging.error('add_walker %s' % result)


    def get_tag_id_by_wristband(self, wristband):
        # TODO
        raise NotImplementedError
