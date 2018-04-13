"""
Make up some fake data for teams and walkers so I can test the DB, changefeeds, etc.
"""

import argparse
import json
import logging
from random import random
import requests
import sys
sys.path.append('..')
from time import sleep

from relay_config import cfg
from relay_websocket import RelayWebsocket

logging.basicConfig(
    name=__name__,
    filename='populate.log',
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(module)s %(message)s'
)

def populate_teams():
	teams = [
	    {'name': '49ers'},
	    {'name': 'Raiders'},
	    {'name': 'Warriors'},
	    {'name': 'Eagles'},
	    {'name': 'Sixers'},
	    {'name': 'Patriots'},
	    {'name': 'Yankees'},
	    {'name': 'Red Sox'},
	    {'name': 'Sharks'},
	    {'name': 'Giants'},
	    {'name': 'Vikings'},
	    {'name': 'Seahawks'},
	    {'name': 'Rams'},
	    {'name': 'Love Your Butt'},
	    {'name': 'Event Staff'}
	]
	for i in range(0, len(teams)):
		teams[i]['id'] = i  # I guess better than a big ugly GUID
	resp = requests.post(cfg.rest_url('/teams'), json=teams)
	return teams


def populate_walkers(teams):
	walkers = []
	used_epcs = []
	for i in range(0, 200):
		while True:  # Find a unique EPC since it's the primary key in the DB
			epc = int(random() * 9999)  # We have four-character strings in the EPC
			if epc not in used_epcs:
				used_epcs.append(epc)
				break
		team_index = int(random() * len(teams))
		team_id = teams[team_index]['id']
		walkers.append({
			'id': epc,
			'team_id': team_id,
		})
	requests.post(cfg.rest_url('/tags'), json=walkers)
	return [w['id'] for w in walkers] 


def walk_laps(tags):
	ws = RelayWebsocket()
	while True:
	    tag = tags[int(random() * len(tags))]
	    ws.send(str(tag))
	    sleep(1)


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Make up some fake data for testing')
	parser.add_argument('--from-scratch', action='store_true', default=False, \
		help='Generate teams and walkers into an empty DB. Otherwise use existing DB')
	ns = parser.parse_args()

	if ns.from_scratch:
		teams = populate_teams()
		tags = populate_walkers(teams)
	else:
		resp = requests.get(cfg.rest_url('/tags'))
		tags = json.loads(resp.text)

	walk_laps(tags)
