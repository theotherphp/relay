import json
import websocket
from relay_config import Config


if __name__ == '__main__':
    cfg = Config()
    info = dict(
        reader_id=0,
        tag_ids=['12345']
    )
    ws = websocket.create_connection(cfg.inventory_url())
    ws.send(json.dumps(info))
