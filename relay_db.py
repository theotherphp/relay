import logging
import rethinkdb as r
from datetime import datetime as dt
import emoji
import time
from tornado.gen import coroutine, Return

from relay_config import cfg

DB_NAME = cfg.db_name
WALKER_TABLE = cfg.walker_table
TEAM_TABLE = cfg.team_table
MIN_LAP_TIME = cfg.min_lap_time
MICROS_PER_SEC = 1000000.0

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
            yield r.table(WALKER_TABLE).index_create('team_id').run(self.conn)
            yield r.table(WALKER_TABLE).index_wait().run(self.conn)
        if TEAM_TABLE not in table_names:
            yield r.db(DB_NAME).table_create(TEAM_TABLE, durability='soft').run(self.conn)
            yield r.table(TEAM_TABLE).index_create('laps').run(self.conn)
            yield r.table(TEAM_TABLE).index_create('avg_laps').run(self.conn)
            yield r.table(TEAM_TABLE).index_wait().run(self.conn)


    @coroutine
    def close(self):
        then = dt.now()
        for table in [WALKER_TABLE, TEAM_TABLE]:
            result = yield r.table(table).sync().run(self.conn)
            if result is None or result.get('synced') != 1:
                log.error('sync %s' % table)
        self.conn.close()
        delta = dt.now() - then
        duration = delta.seconds + (delta.microseconds/MICROS_PER_SEC)
        logging.debug('closed in %f secs' % duration)

 
    def emojize(self, emoji_name):
        emoji_name = emoji_name or 'grinning face'
        cldr_name = ':' + emoji_name.replace(' ', '_') + ':'
        em = emoji.emojize(cldr_name)
        if em == cldr_name:
            logging.warn('no emoji for %s' % emoji_name)
            em = emoji.emojize(':grinning_face:')
        return em


    @coroutine
    def update_emoji(self, team_id, short_name):
        yield r.table(TEAM_TABLE).get(team_id).update({
            'emoji': self.emojize(short_name)
        }).run(self.conn)


    @coroutine
    def insert_teams(self, teams):
        for team in teams:
            team['laps'] = 0
            team['avg_laps'] = 0.0
            if 'id' not in team:
                team['id'] = yield self.get_next_team_id()
            team['emoji'] = self.emojize(team['emoji'])
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


    def append_rank_suffix(self, n):
        # https://stackoverflow.com/questions/3644417/
        return str(n) + ('th' if 4 <= n % 100 <= 20 else {1:'st', 2:'nd', 3:'rd'}.get(n % 10, 'th'))


    @coroutine
    def get_team_rank(self, team_id):
        # Get the offset of the team_id in the team table ordered by lap count
        # TODO: offsets_of doesn't handle ties. Could scan the team table linearly? Ugh.
        offsets = yield r.table(TEAM_TABLE).order_by(r.desc('laps')).offsets_of(
            r.row['id'].eq(team_id)
        ).run(self.conn)
        if offsets is None or len(offsets) != 1:
            logging.error('unexpected offsets: %s' % offsets)
        rank = self.append_rank_suffix(offsets[0] + 1)  # show rank as one-based
        raise Return(rank)


    @coroutine
    def get_next_team_id(self):
        team_with_max_id = yield r.table(TEAM_TABLE).max('id').run(self.conn)
        if team_with_max_id:
            raise Return(team_with_max_id['id'] + 1)
        else:
            raise Return(0)


    @coroutine
    def get_walker(self, walker_id):
        walker = yield r.table(WALKER_TABLE).get(walker_id).run(self.conn)
        raise Return(walker)


    @coroutine
    def get_walkers(self, team_id):
        walkers = []
        cur = yield r.table(WALKER_TABLE).get_all(team_id, index='team_id').run(self.conn)
        while (yield cur.fetch_next()):
            walker = yield cur.next()
            walkers.append(walker)
        raise Return(walkers)


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
        for walker in walkers:
            walker['laps'] = 0
            walker['last_updated_time'] = 0.0
        result = yield r.table(WALKER_TABLE).insert(walkers).run(self.conn)
        if result is None or result.get('errors') != 0:
            logging.error('insert_walkers %s' % result)


    @coroutine 
    def increment_laps(self, tags):
        cur = yield r.table(WALKER_TABLE).get_all(r.args(tags)).run(self.conn)
        if len(tags) > 1:
            logging.debug('updating %d records' % len(tags))
        while (yield cur.fetch_next()):
            walker = yield cur.next()
            tags.remove(walker['id'])  # remove the ones we've seen to find unassigned below
            now = time.time()
            if now - walker['last_updated_time'] > MIN_LAP_TIME:
                # Increment lap totals
                yield r.table(WALKER_TABLE).get(walker['id']).update({
                    'laps': r.row['laps'] + 1,
                    'last_updated_time': now
                }).run(self.conn)
                avg_laps = yield r.table(WALKER_TABLE).get_all(
                    walker['team_id'], index='team_id'
                ).avg('laps').run(self.conn)
                rank = yield self.get_team_rank(walker['team_id'])
                yield r.table(TEAM_TABLE).get(walker['team_id']).update({
                    'avg_laps': avg_laps,
                    'laps': r.row['laps'] + 1,
                    'last_updated_time': now,
                    'rank': rank
                }).run(self.conn)
            else:
                # Not so fast buddy
                d = dt.fromtimestamp(walker['last_updated_time'])
                logging.warn('too soon: %d last lap: %s' % (walker['id'], d.strftime('%x %X')))
        if len(tags) > 0:
            # Shouldn't happen
            logging.warn('unassigned tags: %s' % tags)


    @coroutine
    def zero_all_laps(self):
        yield r.table(WALKER_TABLE).update({
            'laps': 0, 
            'last_updated_time': 0.0, 
        }).run(self.conn)
        yield r.table(TEAM_TABLE).update({
            'laps': 0, 
            'avg_laps': 0.0
        }).run(self.conn)

