"""
Websocket wrapper, adding buffering and reconnect semantics
"""

import websocket
import logging

from tests.relay_config import cfg

class RelayWebsocket(object):

    def __init__(self):
        self.tag_buffer = []
        self.good = False

    def send(self, tag):
        self.tag_buffer.append(tag)
        if not self.good:
            try:
                logging.debug('connecting')
                self.ws = websocket.create_connection(cfg.websocket_url())
                self.ws.on_close = self.on_close
                self.good = True
            except Exception as e:
                logging.error('_connect: %s' % str(e))
        if self.good:
            tags = ','.join(self.tag_buffer)
            logging.info('sending: %s' % tags)
            try:
                self.ws.send(tags)
                self.tag_buffer = []
            except Exception as e:
                self.good = False
                logging.error('send: %s' % str(e))

    def close(self):
        logging.debug('close')
        self.ws.close()
        self.good = False

    def on_close(self):
        logging.debug('on_close')
        self.good = False