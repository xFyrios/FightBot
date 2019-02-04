#!/usr/bin/env python

import fight.attack as a
from random import randint
from math import floor

# This object is used to setup a player for a fight. It is destroyed after the fight.
class Player:
	def __init__(self, uid, name, stats):
		self.uid = int(uid)
		self.name = name # IRC nick
		self.site_username = stats['username']
		self.element_type = int(stats['element_type'])
		self.element_type_name = stats['element_type_name']
		self.health = int(stats['health'])
		self.max_health = int(stats['max_health'])
		self.experience = int(stats['experience'])
		self.level = int(stats['level'])

		self.stats_start = {
			'attack': float(stats['attack']),
			'defense': float(stats['defense']),
			'strength': float(stats['strength']),
			'accuracy': float(stats['accuracy']),
			'speed': float(stats['speed'])
		}
		self.stats = {
			'attack': self.stats_start['attack'],
			'defense': self.stats_start['defense'],
			'strength': self.stats_start['strength'],
			'accuracy': self.stats_start['accuracy'],
			'speed': self.stats_start['speed']
		}
		self.stats_stage = {
			'attack': 0,
			'defense': 0,
			'strength': 0,
			'accuracy': 0,
			'speed': 0
		}
		self.stats_cur_buff = {
			'attack': 0,
			'defense': 0,
			'strength': 0,
			'accuracy': 0,
			'speed': 0
		}
		self.stats_buff_expiry = {}
		
		self.attacks = stats['attacks']
		self.items = []

		self.can_attack = False
		self.run_attempts = 0
		self.undo_buffs = {}
		self.undo_debuffs = {}
		self.effects = {}

	def __str__(self):
		string = "Explorer ID: %d  Name: %s" % (self.uid, self.name)
		if self.name != self.site_username:
			string += " (Username: %s)" % self.site_username
		if self.element_type > 0:
			string += "  Element: %s" % self.element_type_name
		string += "  Health: %s(%d/%d)  Level: %d  XP: %d  |  Attack: %.1f  Defense: %.1f  Strength: %.1f  Accuracy: %.1f  Speed: %.1f  |  Attack Count: %d" % (self.visual_health(False), self.health, self.max_health, self.level, self.experience, self.stats['attack'], self.stats['defense'], self.stats['strength'], self.stats['accuracy'], self.stats['speed'], len(self.attacks))
		if self.effects:
			string += " | Status Ailments: %s" % (", ".join(self.effects.keys()))
		return string

	def display_level(self):
		string = "%s Your Level: %d" % (self.announce_prepend(), self.level)
		return string

	def display_health(self):
		string = "%s Your Health: %s(%d/%d)" % (self.announce_prepend(), self.visual_health(), self.health, self.max_health)
		return string

	def display_full_stats(self, phenny):
		etx = '\x1F'
		phenny.say("%s %s%s's Stats:%s" % (self.announce_prepend(), etx, self.site_username, etx))
		string = "%s Level: %d  XP: %d" % (self.announce_prepend(), self.level, self.experience)
		if self.element_type > 0:
			string += "  Element: %s" % self.element_type_name
		phenny.say(string)
		phenny.say("%s Health: %s(%d/%d)" % (self.announce_prepend(), self.visual_health(), self.health, self.max_health))
		string = "%s Attack: %.1f  Defense: %.1f  Strength: %.1f  Accuracy: %.1f  Speed: %.1f" % (self.announce_prepend(), self.stats['attack'], self.stats['defense'], self.stats['strength'], self.stats['accuracy'], self.stats['speed'])
		phenny.say(string)
		if self.effects:
			phenny.say("%s Status Ailments: %s" % (self.announce_prepend(), ", ".join(self.effects.keys())))

	def visual_health(self, color_bar = True):
		etx = '\x03'
		block = u'\u2588'
		half_block = u'\u258C'
		health_percent = (float(self.health) / float(self.max_health)) * 200
		health_blocks = health_percent / 10
		health_blocks_rounded = int(floor(health_blocks))

		visual_health = u'\uFF5C'
		if color_bar:
			color = self.health_color(health_percent)
			visual_health += etx + color
		visual_health += (block * health_blocks_rounded)
		if health_percent % 10 >= 4:
			visual_health += half_block
			visual_health += (19 - health_blocks_rounded) * " "
		else:
			visual_health += (20 - health_blocks_rounded) * " "
		if color_bar:
			visual_health += etx
		visual_health += u'\uFF5C'
		return visual_health

	@staticmethod
	def health_color(health_percent):
		if health_percent >= 180:
			return "9"
		elif health_percent >= 150:
			return "3"
		elif health_percent >= 100:
			return "8"
		elif health_percent >= 50:
			return "7"
		else:
			return "4"

	@staticmethod
	def announce_prepend():
		etx = '\x03'
		return "%s03-%s" % (etx, etx)

	def attack_options(self, phenny, username):
		options = filter(lambda attack: attack.uses < attack.max_uses, self.attacks)
		if len(options) <= 0:
			self.attacks.append(a.create_last_resort_attack())
		phenny.write(('NOTICE', username + " Choose your move:"))
		i = 0
		for attackid in range(len(self.attacks)):
			i = attackid + 1
			attack = self.attacks[attackid]
			if attack.uses >= attack.max_uses:
				string = " %d - %s [---]" % (i, attack.display_attack_option())
			else:
				string = " %d - %s [!attack %d]" % (i, attack.display_attack_option(), i)
			phenny.write(('NOTICE', username + string))
		phenny.write(('NOTICE', username + " %d - Run [!run]" % (i+1)))


	# Run and Attack functions
	def run(self, monster):
		self.run_attempts += 1
		monster_speed = monster.stats['speed']
		if monster_speed < 1:
			monster_speed = 1
		test = (((self.stats['speed'] * 128) / monster_speed) + 30 * self.run_attempts) % 256
		random_int = randint(0, 255)

		if random_int < test:
			return True
		else:
			return False

	def attack_monster(self, phenny, cur_round, attack, monster):
		restored_health = False
		if attack.health > 0:
			if (self.health + attack.health) > self.max_health:
				self.health = self.max_health
			else:
				self.health += attack.health
			phenny.say("%s You restored %d health!" % (self.announce_prepend(), attack.health))
			restored_health = True

		no_damage = False
		if attack.damage_base > 0:
			damage = floor(2 * max(self.level, 1) / 5 + 2)
			damage = floor(damage * attack.damage_base * max(self.stats['attack'], 1) / max(monster.stats['defense'], 1))
			damage = floor(damage / 50) + 2
			# Critical hit
			if attack.is_critical_hit(self.stats['strength']):
				damage = floor(damage * attack.critical_multiplier)
				phenny.say("%s It was a critical hit!" % self.announce_prepend())
			# Element strengths/weaknesses
			if attack.element_type > 0 and monster.element_type > 0:
				strong_weak = self.element_strong_weak(attack.element_type, monster.element_type)
				if strong_weak and strong_weak == 'strong':
					damage *= 2
					phenny.say("%s It was super effective!" % self.announce_prepend())
				elif strong_weak and strong_weak == 'weak':
					damage = floor(damage / 2)
					phenny.say("%s It was not very effective." % self.announce_prepend())
			# Damage randomizer
			random_int = (float(randint(85,100)) / 100)
			damage = floor(damage * random_int)
			if damage > 0:
				monster.health -= damage
				if monster.health < 0:
					monster.health = 0
				phenny.say('%s %d damage was done to the %s!' % (self.announce_prepend(), damage, monster.name))
				phenny.say(monster.display_health())
			else:
				no_damage = True
		else:
			no_damage = True
		if attack.damage_to_self_percent > 0:
			damage_self = floor(self.max_health * attack.damage_to_self_percent)
			self.health -= damage_self
			if self.health < 0:
				self.health = 0
			phenny.say('%s You were hit with %d recoil damage!' % (self.announce_prepend(), damage_self))
			phenny.say(self.display_health())
		if monster.health > 0:
			buffs_applied = self.apply_attack_buffs(phenny, cur_round, attack, monster)
			effects_applied = self.apply_attack_effects(phenny, cur_round, attack.effects, monster)

		if no_damage and not buffs_applied and not effects_applied and not restored_health:
			phenny.say('%s No damage was done to the %s.' % (self.announce_prepend(), monster.name))

	def apply_attack_buffs(self, phenny, cur_round, attack, monster):
		change_self = False
		change_monster = False
		if attack.buffs_by_stage:
			for stat, buff in attack.buffs_by_stage.items():
				if buff != 0:
					if self.stats_stage[stat] + buff >= 6:
						self.stats_stage[stat] = 6
					elif self.stats_stage[stat] + buff <= -6:
						self.stats_stage[stat] = -6
					else:
						self.stats_stage[stat] += buff
					change_self = True
					self.announce_buff_stage(phenny, stat, buff)
		if attack.buffs:
			for stat, buff in attack.buffs.items():
				if buff != 0 and stat != 'turns':
					self.stats_cur_buff[stat] += buff
					expire_round = int(cur_round + attack.buffs['turns'])
					if expire_round not in self.stats_buff_expiry.keys():
						self.stats_buff_expiry[expire_round] = {}
					self.stats_buff_expiry[expire_round][stat] = buff
					change_self = True
					if buff >= 0:
						phenny.say("%s Your %s stat went up by %.1f levels! This buff will last %d turns." % (self.announce_prepend(), stat, buff, attack.buffs['turns']))
					else:
						phenny.say("%s Your %s stat went down by %.1f levels! This debuff will last %d turns." % (self.announce_prepend(), stat, buff, attack.buffs['turns']))
		if attack.debuffs_by_stage:
			for stat, debuff in attack.debuffs_by_stage.items():
				if debuff != 0:
					if monster.stats_stage[stat] + debuff >= 6:
						monster.stats_stage[stat] = 6
					elif monster.stats_stage[stat] + debuff <= -6:
						monster.stats_stage[stat] = -6
					else:
						monster.stats_stage[stat] += debuff
					change_monster = True
					self.announce_buff_stage(phenny, stat, debuff, monster.name)
		if attack.debuffs:
			for stat, debuff in attack.debuffs.items():
				if debuff != 0 and stat != 'turns':
					monster.stats_cur_buff[stat] -= debuff
					expire_round = int(cur_round + attack.debuffs['turns'])
					if expire_round not in monster.stats_buff_expiry.keys():
						monster.stats_buff_expiry[expire_round] = {}
					monster.stats_buff_expiry[expire_round][stat] = debuff * -1
					change_monster = True
					if debuff >= 0:
						phenny.say("%s The %s's %s stat went down by %.1f levels! This debuff will last %d turns." % (self.announce_prepend(), monster.name, stat, debuff, attack.debuffs['turns']))
					else:
						phenny.say("%s The %s's %s stat went up by %.1f levels! This buff will last %d turns." % (self.announce_prepend(), monster.name, stat, debuff, attack.debuffs['turns']))
		if change_self:
			self.recalculate_stats()
		if change_monster:
			monster.recalculate_stats()
		if change_self or change_monster:
			return True
		else:
			return False

	def apply_attack_effects(self, phenny, cur_round, effects, target):
		major_effects = ['Poison', 'Burn', 'Sleep', 'Freezing']
		change_self = False
		change_target = False

		for effect,chance in effects.items():
			if chance > 0 and randint(1, 100) < chance:
				if effect in major_effects:
					if effect in target.effects.keys():
						# If that status effect is already applied, silently fail
						continue
					# Major effect, check to make sure the target doesn't already have one of these
					intersect = [effect for effect in target.effects.keys() if effect in major_effects] 
					if len(intersect) > 0:
						# Already has a major effect, deny
						phenny.say("%s You tried to use %s but it failed." % (self.announce_prepend(), effect))
					else:
						if effect in ['Poison', 'Burn', 'Freezing']:
							target.effects[effect] = 0 # infinite
							change_target = True
							self.announce_effect(phenny, effect, target.name)
						elif effect == 'Sleep':
							end = int(cur_round + randint(1, 3))
							target.effects[effect] = end
							change_target = True
							self.announce_effect(phenny, effect, target.name)
				else:
					# Minor effects
					if effect in ['CantEscape', 'Embargo', 'HPLeech', 'Blindness', 'Confusion'] and effect in target.effects.keys():
						# If that status effect is already applied, silently fail
						continue
					if effect in ['CantEscape', 'Embargo', 'HPLeech']:
						target.effects[effect] = 0 # infinite
						change_target = True
						self.announce_effect(phenny, effect, target.name)
					elif effect == 'Blindness':
						end = int(cur_round + randint(1, 3))
						target.effects[effect] = end
						change_target = True
						self.announce_effect(phenny, effect, target.name)
					elif effect == 'Confusion':
						end = int(cur_round + randint(1, 4))
						target.effects[effect] = end
						change_target = True
						self.announce_effect(phenny, effect, target.name)
		if change_self or change_target:
			return True
		else:
			return False

	def announce_effect(self, phenny, effect, target_name = False):
		announce_word = {'Poison': 'poisoned', 'Burn': 'burned', 'Freezing': 'frozen', 'Blindness': 'blinded', 'Confusion': 'confused'}
		if target_name:
			string = "The %s " % target_name
		else:
			string = "You "
		if effect in announce_word.keys():
			string += "became %s!" % announce_word[effect]
		elif effect == "Sleep":
			string += "fell asleep!"
		elif effect == 'HPLeech':
			if target_name:
				string += "was seeded!"
			else:
				string += "were seeded!"
		elif effect == 'CantEscape':
			if target_name:
				string += "was blocked! It can no longer run from the battle."
			else:
				string += "were blocked! You can no longer run from the battle."
		elif effect == 'Embargo':
			string += "can't use items anymore!"
		phenny.say("%s %s" % (self.announce_prepend(), string))


	def announce_buff_stage(self, phenny, stat, buff_stage, target_name = False):
		if target_name:
			string = "The %s's %s " % (target_name, stat)
		else:
			string = "Your %s " % stat
		if buff_stage == 1:
			if randint(0,1) == 1:
				string += "rose!"
			else:
				string += "went up!"
		elif buff_stage == 2:
			rand_int = randint(0,2)
			if rand_int == 1:
				string += "greatly rose!"
			elif rand_int == 2:
				string += "went way up!"
			else:
				string += "sharply rose!"
		elif buff_stage >= 3:
			string += "rose drastically!"
		elif buff_stage == -1:
			string += "fell!"
		elif buff_stage == -2:
			rand_int = randint(0,2)
			if rand_int == 1:
				string += "greatly fell!"
			elif rand_int == 2:
				string += "sharply fell!"
			else:
				string += "harshly fell!"
		elif buff_stage <= -3:
			string += "severely fell!"
		phenny.say("%s %s" % (self.announce_prepend(), string))

	def expire_buffs(self, phenny, cur_round):
		change = False
		if self.stats_buff_expiry:
			for exp_round, expire_dict in self.stats_buff_expiry.items():
				if exp_round < cur_round:
					change = True
					for stat, buff in expire_dict.items():
						self.stats_cur_buff[stat] -= buff
						if buff > 0:
							phenny.say("%s A buff expired. Your %s went back down %.1f levels." % (self.announce_prepend(), stat, buff))
						else:
							phenny.say("%s A debuff expired. Your %s went back up %.1f levels." % (self.announce_prepend(), stat, buff * -1))
					del self.stats_buff_expiry[exp_round]
		if change:
			self.recalculate_stats()

	def expire_effects(self, phenny, cur_round):
		announce_word = {'Blindness': 'blinded', 'Confusion': 'confused'}
		change = False
		if self.effects:
			for effect, exp_round in self.effects.items():
				if exp_round > 0 and exp_round < cur_round:
					change = True
					del self.effects[effect]
					if effect in announce_word.keys():
						phenny.say("%s You are no longer %s!" % (self.announce_prepend(), announce_word[effect]))
					elif effect == 'Sleep':
						phenny.say("%s You woke up!" % self.announce_prepend())

	def recalculate_stats(self):
		for stat, value in self.stats.items():
			starting_value = self.stats_start[stat]
			new_value = starting_value
			stage = self.stats_stage[stat]
			buff = self.stats_cur_buff[stat]

			if stage != 0:
				new_value = self.buff_stage_multiplier(starting_value, stage)
			new_value += buff
			self.stats[stat] = max(new_value, 0)


	@staticmethod
	def buff_stage_multiplier(stat, stage):
		multipliers = {6: 8.0/2.0, 5: 7.0/2.0, 4: 6.0/2.0, 3: 5.0/2.0, 2: 4.0/2.0, 1: 3.0/2.0, -1: 2.0/3.0, -2: 2.0/4.0, -3: 2.0/5.0, -4: 2.0/6.0, -5: 2.0/7.0, -6: 2.0/8.0}

		if stage == 0:
			return stat
		elif stage > 6:
			stage = 6
		elif stage < -6:
			stage = -6

		multiplier = multipliers[stage]
		return float(stat) * multiplier
		

	# Test if an attacks element is strong or weak against a targets element
	# Returns 'strong', 'weak', or False if neither
	@staticmethod
	def element_strong_weak(attack_element, target_element):
		# 1 => 'Earth', 2 => 'Wind', 3 => 'Fire', 4 => 'Water'
		# Water > Fire > Earth > Wind > Water
		if attack_element == 4: # Water
			if target_element == 3: # > Fire
				return 'strong'
			elif target_element == 2: # < Wind
				return 'weak'

		elif attack_element == 3: # Fire
			if target_element == 1: # > Earth
				return 'strong'
			elif target_element == 4: # < Water
				return 'weak'

		elif attack_element == 1: # Earth
			if target_element == 2: # > Wind
				return 'strong'
			elif target_element == 3: # < Fire
				return 'weak'

		elif attack_element == 2: # Wind
			if target_element == 4: # > Water
				return 'strong'
			elif target_element == 1: # < Earth
				return 'weak'
		else:
			return False

	def calculate_experience_gain(self, monster):
		base = (monster.experience * monster.level) / 5
		level_mod = ((2 * monster.level + 10) ** 2.5) / ((monster.level + self.level + 10) ** 2.5)
		experience = floor(base * level_mod + 1)
		return experience


# BASIC FUNCTIONS
def create_player(phenny, uid, username):
	stats = get_user_stats(phenny, uid, username)
	if stats == False:
		return False
	else:
		current_player = Player(uid, username, stats)
		return current_player

def get_user_stats(phenny, uid, username):
	stats = {}
	print uid
	site = phenny.callGazelleApi({'uid': uid, 'action': 'fightUserStats'})

	if site == False:
		phenny.write(('NOTICE', username + " An error occurred trying to get your user stats."))
		return False
	elif site['status'] == "error":
		error_msg = site['error']
		phenny.write(('NOTICE', username + " Error: " + error_msg)) 
		return False
	else:
		stats['username'] = site['username']
		stats['element_type'] = site['element_type']
		stats['element_type_name'] = site['element_type_name']
		stats['health'] = site['health']
		stats['max_health'] = site['max_health']
		stats['experience'] = site['experience']
		stats['level'] = site['level']
		stats['attack'] = site['attack']
		stats['defense'] = site['defense']
		stats['strength'] = site['strength']
		stats['accuracy'] = site['accuracy']
		stats['speed'] = site['speed']
		stats['attacks'] = []
		for attackid in site['attacks']:
			stats['attacks'].append(a.create_attack(phenny, int(attackid), username))

		return stats


if __name__ == '__main__':
    print(__doc__)
