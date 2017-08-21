import logging
import rethinkdb as r
from datetime import datetime as dt
import time

DB_NAME = 'relay'
WALKER_TABLE = 'walkers'
TEAM_TABLE = 'teams'
MICROS_PER_SEC = 1000000.0
LAP_DEDUPLICATION_THRESHOLD = 2  # *60  # 2 minutes


class RelayDB:
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
        else:
            generated_keys = result['generated_keys']
        return generated_keys


    def get_teams(self):
        return r.table(TEAM_TABLE).run()


    def get_teams_by(self, attrib, count):
        return list(
            r.table(TEAM_TABLE).with_fields('name', 'laps', 'css_class')
            .filter(r.row['laps'] > 0)
            .order_by(r.desc('laps'))
            .limit(count)
            .run()
        )

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
        # else:
        #     walker_id = result['generated_keys'][0] if 'generated_keys' in result else walker['id']
        #     logging.debug('add walker %s %s' % (walker['name'], walker_id))


    def get_walkers_by(self, attrib, count):
        walkers = list(
            r.table(WALKER_TABLE)
            .filter(r.row['laps'] > 0)
            .order_by(r.desc(attrib))
            .limit(count)
            .run()
        )
        for w in walkers:
            t = self._get_team_id_map(w['team_id'])
            w['team_name'] = t['name']
            w['css_class'] = t['css_class']
        return walkers


    def _get_team_id_map(self, team_id):
        """
        Cache this lookup table so we don't have to hit the DB for every row in the
        leaderboard. Maybe there's a better way. Maybe doesn't matter for changefeeds
        """
        if self.team_id_map is None:
            self.team_id_map = {
                t['id']: {'name': t['name'], 'css_class': t['css_class']}\
                for t in r.table('teams').with_fields('name', 'id', 'css_class').run()
            }
        return self.team_id_map[team_id]


    def get_tag_id_by_wristband(self, wristband):
        # TODO
        raise NotImplementedError


    def post_laps(self, rfid_tags):
        now = time.time()  # sidestepping the whole timezone mess
        for tag in rfid_tags:
            walker = r.table(WALKER_TABLE).get(tag).run()
            if walker is None:
                logging.warn('no walker for tag %s' % tag)
                continue
            winfo = 'name: %s tag: %s' % (walker['name'], tag)
            delta = dt.fromtimestamp(now) - dt.fromtimestamp(walker['last_updated_time'])

            if delta.total_seconds() > LAP_DEDUPLICATION_THRESHOLD:
                # Update walker lap total
                # logging.debug('posting lap for %s' % winfo)
                changes = r.table(WALKER_TABLE).get(tag).update({
                    'laps': r.row['laps'] + 1,
                    'last_updated_time': now
                }).run()
                if changes['errors'] != 0:
                    log.error('post_laps error for %s changes: %s' % (winfo, changes))

                # Update team lap total
                changes = r.table(TEAM_TABLE).get(
                    walker['team_id']
                ).update(
                    {'laps': r.row['laps'] + 1}
                ).run()
                if changes['errors'] != 0:
                    log.error('updating team laps for %s changes: %s' % (winfo, changes))
            else:
                logging.warn('duplicate lap ignored for %s' % winfo)
