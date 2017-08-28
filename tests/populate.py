"""
Make up some fake data for teams and walkers so I can test the DB, changefeeds, etc.
"""

from random import random
from time import sleep
import requests
import json
import websocket
import argparse

from relay_config import Config

def populate_teams():
	teams = [
	    {
	        'name': '49ers',
	        'captain': 'Joe Montana',
	    },
	    {
	        'name': 'Raiders',
	        'captain': 'Derek Carr',
	    },
	    {
	        'name': 'Warriors',
	        'captain': 'Steph Curry',
	    },
	    {
	        'name': 'Eagles',
	        'captain': 'Ron Jaworski',
	    },
	    {
	        'name': 'Sixers',
	        'captain': 'Julius Erving',
	    },
	    {
	        'name': 'Patriots',
	        'captain': 'Tom Brady',
	    },
	    {
	        'name': 'Yankees',
	        'captain': 'Derek Jeter',
	    },
	    {
	        'name': 'Red Sox',
	        'captain': 'Roger Clemens',
	    },
	    {
	        'name': 'Sharks',
	        'captain': 'Joe Thornton',
	    },
	    {
	        'name': 'Giants',
	        'captain': 'Buster Posey',
	    },
	]
	cfg = Config()
	resp = requests.post(cfg.rest_url('/teams'), json=teams)
	for i in range(0, len(teams)):
		teams[i]['id'] = i  # hack
	return teams


def populate_walkers(teams):

	with open('last_names.csv', 'rb') as f:
		last_names = f.read().split('\r\n')
		f.close()

	with open('male_first_names.csv', 'rb') as f:
		male_first_names = f.read().split('\r\n')
		f.close()

	with open('female_first_names.csv', 'rb') as f:
		female_first_names = f.read().split('\r\n')
		f.close()

	names = []
	for i in range(0,100):
		name = male_first_names[int(random() * len(male_first_names))].title() + ' ' + \
			last_names[int(random() * len(last_names))]
		if not name in names:
			names.append(name)

		name = female_first_names[int(random() * len(female_first_names))].title() + ' ' + \
			last_names[int(random() * len(last_names))]
		if not name in names:
			names.append(name)

	walkers = {}
	count = 0
	for name in names:
		tag_id = str(int(random() * 1000000000))  # fake RFID EPC
		count = count + 1 
		team_index = int(random() * len(teams))
		walkers[tag_id] = {
			'name' : name,
			'team_id': teams[team_index]['id'],
			'wristband': count
		}

	cfg = Config()
	for k,v in walkers.iteritems():
		payload = {'name': v['name'], 'team_id': v['team_id'], 'wristband': v['wristband'], 'id': k}
		requests.post(cfg.rest_url('/register'), payload)
		sleep(0.1)

	return walkers.keys()


def walk_laps(tag_ids):
	cfg = Config()
	ws = websocket.create_connection(cfg.websocket_url())
	while True:
	    tag = tag_ids[int(random() * len(tag_ids))]
	    ws.send(tag)
	    sleep(1)


if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Make up some fake data for testing')
	parser.add_argument('--from-scratch', action='store_true', default=False, \
		help='Generate teams and walkers into an empty DB. Otherwise use existing DB')
	ns = parser.parse_args()

	cfg = Config()
	if ns.from_scratch:
		teams = populate_teams()
		tag_ids = populate_walkers(teams)
	else:
		resp = requests.get(cfg.rest_url('/tags'))
		tag_ids = json.loads(resp.text)

	walk_laps(tag_ids)
