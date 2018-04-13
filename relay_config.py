"""
Configure global stuff like hostname and port
"""

class Config(object):
    @property
    def app_host(self):
        return 'relay.local'

    @property
    def app_port(self):
        return '8888'

    @property
    def db_host(self):
        return 'localhost'

    @property
    def db_port(self):
        return '28015'

    @property
    def db_name(self):
        return 'relay'

    @property
    def walker_table(self):
        return 'walkers'

    @property
    def team_table(self):
        return 'teams'

    def rest_url(self, api):
        return 'http://' + self.app_host + ':' + self.app_port + api

    def ws_url(self, api):
        return 'ws://' + self.app_host + ':' + self.app_port + api

    @property
    def min_lap_time(self):
        return 6.0  # seconds
    
cfg = Config()
