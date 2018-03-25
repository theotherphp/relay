"""
Websocket wrapper, adding buffering and reconnect semantics
"""

import websocket
import logging

from relay_config import cfg

class RelayWebsocket(object):

    def __init__(self):
        self.tag_buffer = []
        self.good = False

    def send(self, tag):
        self.tag_buffer.append(tag)
        if not self.good:
            try:
                logging.debug('connecting')
                self.ws = websocket.create_connection(cfg.laps_ws_url)
                self.ws.on_close = self.on_close
                self.good = True
            except Exception as e:
                logging.error('_connect: %s' % str(e))
        if self.good:
            tags = ','.join(self.tag_buffer)
            num_tags = len(self.tag_buffer)
            if num_tags > 1:
                logging.debug('sending %d tags' % num_tags)
            try:
                self.ws.send(tags)
                self.tag_buffer = []
            except Exception as e:
                self.good = False
                logging.error('send: %s' % str(e))

    def close(self):
        logging.debug('close')
        if self.good:
            self.ws.close()
        self.good = False

    def on_close(self):
        logging.debug('on_close')
        self.good = False
