#!/usr/bin/env python

from random import choice as random_choice, randint

# This object is used to setup a new realm

class Realm:
	def __init__(self, id, name, level, cost, monsters):
		self.id = int(id)
		self.name = name
		self.level = int(level)
		self.hunt_cost = int(cost)
		self.monsters = monsters

	def __str__(self):
		monster_count = len(self.monsters)
		string = "Realm ID: %d  Name: %s  Suggested Level: %d  Hunt Cost: %d  Monster Count: %d" % (self.id, self.colored_name, self.level, self.hunt_cost, monster_count)
		return string

	def get_id(self):
		return self.id

	@property
	def colored_name(self):
		return self.color_realm_name(self.name, self.level)

	def announce(self, phenny):
		phenny.say("You have entered a new realm! Welcome to the %s." % self.colored_name)
		phenny.say("Minimum Suggested Level: %d  Hunt Cost: %d" % (self.level, self.hunt_cost))

	def info(self, phenny):
		phenny.say("You are currently in the %s realm." % self.colored_name)
		phenny.say("Minimum Suggested Level: %d  Hunt Cost: %d" % (self.level, self.hunt_cost))

	def explore(self, phenny, userid, username):
		if len(self.monsters) <= 0:
			phenny.say("There appear to be no monsters in this realm... Yay?")
			return False
		if self.hunt_cost > 0:
			success = phenny.callGazelleApi({'action': 'huntCost', 'userid': userid, 'cost': self.hunt_cost})
			if not success or 'status' not in success:
				phenny.write(('NOTICE', username + ' Something went wrong and your exploration failed.'))
			elif success['status'] == 'ok':
				phenny.write(('NOTICE', username + ' You were charged ' + str(self.hunt_cost) + ' gold for your exploration.'))
			elif 'error' in success:
				phenny.write(('NOTICE', username + ' Error: ' + success['error']))
			else:
				phenny.write(('NOTICE', username + ' Something went wrong and your exploration failed.'))
				return False

		# 75% chance of finding a monster
		if randint(0,3) >= 1:
			monster = random_choice(self.monsters)
			return monster
		else:
			phenny.say("You spent time exploring the realm but found no creatures! :(")
			return False

	@staticmethod
	def color_realm_name(name, level):
		etx = '\x03'
		if level < 3:
			color = "09,01"
		elif level < 5:
			color = "03,01"
		elif level < 10:
			color = "10,01"
		elif level < 25:
			color = "08,01"
		elif level < 40:
			color = "07,01"
		elif level < 60:
			color = "04,01"
		elif level < 80:
			color = "06,01"
		else:
			color = "05,01"
		return "{0}{1} {2} {0}".format(etx, color, name)


# BASIC FUNCTIONS
def create(id, name, level, cost, monsters):
	monsters_list = []
	for monsterid, amount in monsters.items():
		monsters_list += int(amount) * [int(monsterid)]
	return Realm(id, name, level, cost, monsters_list)


if __name__ == '__main__':
    print(__doc__)
