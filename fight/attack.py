#!/usr/bin/env python

from random import randint

ELEM_EARTH = 1
ELEM_WIND = 2
ELEM_FIRE = 3
ELEM_WATER = 4

# This object is used to setup attacks both for players and monsters
class Attack:
	def __init__(self, stats):
		self.id = int(stats['id'])
		self.name = stats['name']
		self.type = stats['type']
		self.element_type = int(stats['element_type'])
		self.element_type_name = stats['element_type_name']
		self.damage_base = int(stats['damage_base'])
		self.damage_to_self = int(stats['damage_to_self'])
		self.damage_to_self_percent = float(stats['damage_to_self_percent'])
		self.accuracy = int(stats['accuracy'])
		self.priority = int(stats['priority'])
		self.high_critical_chance = bool(stats['high_critical_chance'])
		self.critical_multiplier = float(stats['critical_multiplier'])
		self.health = int(stats['health'])
		self.max_uses = int(stats['max_uses'])
		self.uses = 0
		self.realm_requirement = int(stats['realm_requirement'])
		self.realm_requirement_name = stats['realm_requirement_name']
		self.buffs = stats['buffs']
		self.debuffs = stats['debuffs']
		self.buffs_by_stage = stats['buffs_by_stage']
		self.debuffs_by_stage = stats['debuffs_by_stage']
		self.effects = stats['effects']
		
		self.is_item = False
		self.item_id = False

		for key,v in self.effects.items():
			self.effects[key] = int(self.effects[key])
		for key,v in self.buffs.items():
			if key == 'turns':
				self.buffs[key] = int(self.buffs[key])
			else:
				self.buffs[key] = float(self.buffs[key])
		for key,v in self.debuffs.items():
			if key == 'turns':
				self.debuffs[key] = int(self.debuffs[key])
			else:
				self.debuffs[key] = float(self.debuffs[key])


	def __str__(self):
		string = "Attack ID: %d  Name: %s  Type: %s" % (self.id, self.name, self.type)
		if self.element_type > 0:
			string += "  Element: %s" % self.element_type_name

		string += " | Base Damage: %d  Accuracy: %d  Priority: %d" % (self.damage_base, self.accuracy, self.priority)
		if self.health > 0:
			string += "  Heal: %d" % self.health
		string += "  Uses: %d / %d  Critical Hit Multiplier: %.2f" % (self.uses, self.max_uses, self.critical_multiplier)
		if self.high_critical_chance:
			string += " [High Chance]"
		if self.realm_requirement > 0:
			string += " Realm Required: %s" % self.realm_requirement_name

		has_buffs_by_stage = False
		has_debuffs_by_stage = False
		string += " | "
		for buff_name, buff in self.buffs_by_stage.items():
			if buff != 0:
				sign = '+' if buff > 0 else ''
				string += "%s Buff: %s%d " % (buff_name.capitalize(), sign, buff)
				has_buffs_by_stage = True
		else:
			string += "No Buffs (by stage) "
		string += "| "
		for debuff_name, debuff in self.debuffs_by_stage.items():
			if debuff != 0:
				sign = '+' if debuff > 0 else ''
				string += "%s Debuff: %s%d " % (debuff_name.capitalize(), sign, debuff)
				has_debuffs_by_stage = True
		else:
			string += "No Debuffs (by stage) "
		string += "| "

		has_buffs = False
		has_debuffs = False
		for buff_name, buff in self.buffs.items():
			if buff_name != "turns" and buff > 0:
				string += "%s Buff: %.2f " % (buff_name.capitalize(), buff)
				has_buffs = True
		if has_buffs:
			string += "(buffs last %d turns) " % self.buffs['turns']
		else:
			string += "No Buffs (by level) "
		string += "| "
		for debuff_name, debuff in self.debuffs.items():
			if debuff_name != "turns" and debuff > 0:
				string += "%s Debuff: %.2f " % (debuff_name.capitalize(), debuff)
				has_debuffs = True
		if has_debuffs:
			string += "(debuffs last %d turns) " % self.debuffs['turns']
		else:
			string += "No Debuffs (by level) "
		string += "| "

		has_effects = False
		for effect_name, effect in self.effects.items():
			if effect > 0:
				string += "%s Effect: %d%% chance " % (effect_name, effect)
				has_effects = True
		if not has_effects:
			string += "No Effects "
		string += "| "

		return string

	def display_attack_option(self):
		string = "%s (%d/%d)" % (self.name, self.uses, self.max_uses)
		return string

	def is_critical_hit(self, strength):
		threshold = strength
		if self.high_critical_chance:
			threshold *= 6
		return randint(0, 30) < threshold

	def is_strong_against(self, target_element):
		"""Test if an attacks element is strong against target element"""
		# Water > Fire > Earth > Wind > Water
		if self.element_type == 0 or target_element == 0:
			return False
		if (self.element_type, target_element) in (
					(ELEM_WATER, ELEM_FIRE),
					(ELEM_FIRE, ELEM_EARTH),
					(ELEM_EARTH, ELEM_WIND),
					(ELEM_WIND, ELEM_WATER)):
			return True

	def is_weak_against(self, target_element):
		"""Test if an attacks element is weak against target element"""
		# Water > Fire > Earth > Wind > Water
		if self.element_type == 0 or target_element == 0:
			return False
		if (self.element_type, target_element) in (
				(ELEM_WATER, ELEM_WIND),
				(ELEM_FIRE, ELEM_WATER),
				(ELEM_EARTH, ELEM_FIRE),
				(ELEM_WIND, ELEM_EARTH)):
			return True


# BASIC FUNCTIONS
def create_attack(phenny, attackid, username):
	stats = phenny.callGazelleApi({'attackid': attackid, 'action': 'fightAttack'})
	if not stats or 'status' not in stats or stats['status'] == "error":
		phenny.write(('NOTICE', "%s Error: One of your attacks could not load properly. (Attack ID: %d)" % (username, attackid)))
		return False

	if 'damage_to_self_percent' not in stats:
		stats['damage_to_self_percent'] = 0
	return Attack(stats)

# an attack you receive if you no longer have any attacks with uses left
def create_last_resort_attack():
	stats = {
		"id": 100000,
		"name": "Struggle",
		"type": "Physical - Brute",
		"element_type": 0,
		"element_type_name": "",
		"damage_base": 50,
		"accuracy": 99,
		"priority": 100,
		"high_critical_chance": False,
		"critical_multiplier": 1.5,
		"health": 0,
		"damage_to_self": 0,
		"damage_to_self_percent": 0.25,
		"max_uses": 10,
		"realm_requirement": 0,
		"realm_requirement_name": "",
		"buffs": {
			"attack": 0,
			"defense": 0,
			"strength": 0,
			"accuracy": 0,
			"speed": 0,
			"turns": 1
		},
		"debuffs": {
			"attack": 0,
			"defense": 0,
			"strength": 0,
			"accuracy": 0,
			"speed": 0,
			"turns": 1
		},
		"buffs_by_stage": {
			"attack": 0,
			"defense": 0,
			"strength": 0,
			"accuracy": 0,
			"speed": 0
		},
		"debuffs_by_stage": {
			"attack": 0,
			"defense": 0,
			"strength": 0,
			"accuracy": 0,
			"speed": 0
		},
		"effects": {
			"Sleep": 0,
			"Poison": 0,
			"Burn": 0,
			"Freezing": 0,
			"HPLeech": 0,
			"Confusion": 0,
			"Flinching": 0,
			"Blindness": 0,
			"CantEscape": 0,
			"Embargo": 0
		}
	}
	new_attack = Attack(stats)
	return new_attack

if __name__ == '__main__':
    print(__doc__)
