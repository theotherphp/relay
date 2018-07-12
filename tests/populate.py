"""
Make up some fake data for teams and walkers so I can test the DB, changefeeds, etc.
"""

import argparse
import csv
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


def teams_from_csv(fname):
	teams = []
	count = 0
	with open(fname, 'rU') as csvfile:
		reader = csv.DictReader(csvfile)
		for d in reader:
			if 'dollars' in d:
				del d['dollars']
			if 'members' in d:
				d['members'] = int(d['members'])
			d['id'] = count
			count += 1
			teams.append(d)
	return teams


def populate_walkers(teams, random=False):
	walkers = []
	used_epcs = []

	if random:
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
	else:
		for team in teams:
			if team.get('tags') is '':
				continue
			l = [int(t) for t in team['tags'].split('-')]
			tags = range(min(l), max(l) + 1)
			for tag in tags:
				if tag in used_epcs:
					logging.error('duplicate tag %d in team %s' % tag, team['name'])
				else:
					used_epcs.append(tag)
					walkers.append(dict(id=tag, team_id=team['id']))

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
	parser.add_argument(
		'--csv-file', default='',
		help='Pathname to CSV file'
	)
	parser.add_argument(
		'--walk', default=False,
		help='Start walking?'
	)
	ns = parser.parse_args()

	if ns.csv_file:
		teams = teams_from_csv(ns.csv_file)
		resp = requests.post(cfg.rest_url('/teams/'), json=teams)
		tags = populate_walkers(teams)
	else:
		resp = requests.get(cfg.rest_url('/tags'))
		tags = json.loads(resp.text)

	if ns.walk:
		walk_laps(tags)
