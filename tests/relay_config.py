"""
Configure global stuff like hostname and port
"""

import platform


class Config(object):
    @property
    def app_host(self):
        s = platform.system()
        if s == 'Darwin':
            return '10.0.1.20'
        elif s == 'Linux':
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
        
    def websocket_url(self):
        return 'ws://' + self.app_host + ':' + self.app_port + '/leaderboard_ws'

    def rest_url(self, api):
        return 'http://' + self.app_host + ':' + self.app_port + api

    def inventory_url(self):
        return 'ws://' + self.app_host + ':' + self.app_port + '/inventory_ws'
