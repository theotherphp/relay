"""
Read and write RFID tags for the Relay app
"""

from functools import partial
import logging
from signal import signal, SIGTERM, SIGINT
import sys
import time

import mercury
from relay_config import Config
from relay_websocket import RelayWebsocket

logging.basicConfig(
    name=__name__,
    filename='rfid.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)

cfg = Config()
ws = None
dedup_cache = {}
DEDUP_THRESHOLD = 5.0


def post(epc_obj):
    epc = repr(epc_obj).strip('\'')  # ugh
    hex_numbers = [epc[i:i+2] for i in range(0, len(epc), 2)]
    chars = [chr(int(ch, 16)) for ch in hex_numbers]
    tag = ''.join(chars)
    now = time.time()
    if now - dedup_cache.get(tag, 0.0) > DEDUP_THRESHOLD:
        dedup_cache[tag] = now
        if ws:
            ws.send(tag)
    else:
        logging.debug('duplicate read %s' % tag)


def sig_handler(sig, frame):
    logging.info('caught signal %d' % sig)
    sys.exit(0)



if __name__ == '__main__':
    logging.info('starting')
    reader = None

    signal(SIGTERM, partial(sig_handler))
    signal(SIGINT, partial(sig_handler))

    try:
        reader = mercury.Reader('tmr:///dev/ttyUSB0')
        reader.set_region('NA2')
        reader.set_read_plan([1], 'GEN2', read_power=2600)
        reader.start_reading(post, on_time=250, off_time=250)
        ws = RelayWebsocket()
    except Exception as e:
        logging.error(str(e))

    try:
        while True:
            time.sleep(60)
    finally:
        logging.info('exiting')
        if reader:
            reader.stop_reading()
        if ws:
            ws.close()
