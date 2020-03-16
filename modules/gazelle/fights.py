#!/usr/bin/env python

import fight.player as p, fight.monster as m, fight.realm
from collections import OrderedDict
from random import randint
from math import floor
from threading import Timer

REALM_CYCLE = 60 * 60 * 6  # How often to cycle to a new realm (6 hours)
REALM_CYCLE_RETRY = 60 * 60
ATTACK_TIMEOUT = 120 # How long a player has to choose an attack before a random attack will be chosen for them

game_started = False  # set to true after !start has been called
current_realm = False  # holds the realm object
open_realm = False # if True, users can user !setrealm to change the current realm to a new one
lock_realm = False # if the realm has been blocked from auto cycling to a new one
ongoing_fights = {} # holds the player and monster objects for ongoing fights. 
					# The key for each fight is the users id, the value is another dictionary 
					# with Player under key 'player', and Monster under 'monster':  {userid: {'player': Player, 'monster': Monster, 'data': {}}}
					# 'data' can hold miscellaneous data such as the round #

arguments = {'start': 0, 'setrealm': 1, 'openrealm': 0, 'unopenrealm': 0, 'realmlock': 0, 'realmunlock': 0, 'info': 0, 'fights': 0, 'explore': 0, 'stats': 0, 'run': 0, 'attack': 1, 'items': 0, 'item': 1}
help = OrderedDict([('start', "If adventuring has not already begun, use !start to get the bot going."),
					('info', "To get info on the current realm you are exploring, use the !info or !status command."),
					('explore', "To attempt a hunt, use the command !explore or !hunt."),
					('pstats', "Show your full player stats with !stats. Only works when you are in a fight. Alternative: !mystats or !u"),
					('mstats', "Show the monsters full stats (that you are versing) with !mstats. Only works when you are in a fight. Alternative: !cstats or !mu"),
					('items', "Shows a list of your items that you can use in battle. Only works when you are in a fight."),
					('attack', "To attack a creature use the command !attack #, where # is the number of the attack. Only works when you are in a fight."),
					('item', "To attack a creature with an item use the command !item #, where # is the number of the item. Only works when you are in a fight."),
					('run', "Attempt to !run from a monster. Only works when you are in a fight and it is your turn to attack."),
					('fights', "Shows a list of all currently running fights and who is involved."),
					('setrealm', "To change to a new realm, use !setrealm realmid. Only useable by mods unless a mod has ran !openrealm."),
					('openrealm', "Opens the bot to realm changes by users. Only useable by mods."),
					('unopenrealm', "Unopens the bot to realm changes by users. Only useable by mods."),
					('realmlock', "To stop the realm from changing once every %d hours, use !realmlock. To unlock it again, use !realmunlock. Only useable by mods." % REALM_CYCLE)])

#Used for creating an effectless timer at the start. Probably can be replaced by a less hacky thing.
def dummy_func():
	return
realm_switch_timer = Timer(REALM_CYCLE, dummy_func)

# Turn the system on
def start(phenny, input):
	global game_started
	if game_started:
		phenny.say("The adventure has already begun! Type !commands to get started.") 
	else:
		game_started = True
		create_new_realm(phenny)
start.commands = ['start']
start.priority = 'low'
start.example = '!start'

# Help commands
def fight_help(phenny, input):
    if not input.group(2):
        phenny.say('Commands I recognize include: ' + ', '.join(help.keys()))
        phenny.say("For more info on a command, type '!help cmd' where cmd is the name of the command you want help for.")
    else:
        cmd = input.group(2)
        if cmd in help.keys():
            phenny.say(help[cmd])
        else:
            phenny.say('That command does not exist.')
            phenny.say('Commands I recognize include: ' + ', '.join(help.keys()))
fight_help.commands = ['help', 'fighthelp', 'commands']
fight_help.priority = 'low'
fight_help.example = '!help info'


# Get info on the current realm
def info(phenny, input):
	global game_started
	if not game_started:
		phenny.say("There is currently no adventure in progress. Use !start to get started.")
	elif not current_realm:
		phenny.say("You are currently not in a realm. This should not be possible... I suggest you notify staff.")
	else:
		current_realm.info(phenny)
info.commands = ['info', 'status']
info.priority = 'low'
info.example = '!info'

# Get info on currently running fights
def fights(phenny, input):
	global game_started
	if not game_started:
		phenny.say("There is currently no adventure in progress. Use !start to get started.")
	elif not ongoing_fights:
		phenny.say("There are currently no fights running.")
	else:
		if len(ongoing_fights) > 1:
			phenny.say("There are currently %d fights ongoing." % len(ongoing_fights))
		else:
			phenny.say("There is currently 1 fight ongoing.")
		phenny.say("Fights: " + ', '.join(("%s vs. %s" % (fight['player'].name, fight['monster'].name)) for (key,fight) in ongoing_fights.items()))
fights.commands = ['fights']
fights.priority = 'low'
fights.example = '!fights'


# Set a new realm manually
def set_realm(phenny, input):
	args = check_args(phenny, input.group(0))
	if args:
		realmid = args[0]
		set_new_realm(phenny, input.mod, realmid)
set_realm.commands = ['setrealm']
set_realm.priority = 'low'
set_realm.example = '!realm 1'

# Opens the realm to user changes
def open_realm(phenny, input):
	global open_realm

	if input.mod and game_started:
		open_realm = True
		phenny.say("The channel has been opened to user realm changes.")
open_realm.commands = ['openrealm', 'realmopen']
open_realm.priority = 'low'
open_realm.example = '!openrealm'

# Unopens the realm to user changes
def unopen_realm(phenny, input):
	global open_realm

	if input.mod and game_started:
		open_realm = False
		phenny.say("Users will no longer be able to change the realm.")
unopen_realm.commands = ['unopenrealm', 'realmunopen']
unopen_realm.priority = 'low'
unopen_realm.example = '!unopenrealm'

# Lock the realm so it won't cycle
def realm_lock(phenny, input):
	global lock_realm

	if input.mod and game_started:
		lock_realm = True
		phenny.write(('NOTICE', input.nick + " Lock applied. The realm will no longer auto-cycle."))
realm_lock.commands = ['realmlock', 'lockrealm']
realm_lock.priority = 'low'
realm_lock.example = '!realmlock'

# Unlock the realm so it will start cycling again
def realm_unlock(phenny, input):
	global lock_realm

	if input.mod and game_started:
		lock_realm = False
		phenny.write(('NOTICE', input.nick + " Lock removed. The realm will once again auto-cycle."))
realm_unlock.commands = ['realmunlock', 'unlockrealm']
realm_unlock.priority = 'low'
realm_unlock.example = '!realmunlock'

# The !explore command, to initiate a fight. Charges the player gold
def explore(phenny, input):
	if not game_started:
		phenny.say("There is currently no adventure in progress. Use !start to get started.") 
	elif input.uid in ongoing_fights:
		phenny.say("You can't keep exploring... you are already in a fight!") 
	elif input.uid:
		userid = input.uid
		username = input.nick
		monster_id = current_realm.explore(phenny, userid, username)
		if monster_id:
			# Create the player and monster objects, add them to the ongoing_fights dictionary
			print 'New Fight!'
			player = p.create_player(phenny, userid, username)
			if not player:
				return False
			
			print u'%s' % player
			monster = m.create_monster(phenny, monster_id, username)
			monster.announce(phenny)
			print u'%s' % monster
			ongoing_fights[input.uid] = {
				'player': player,
				'monster': monster,
				'data': {
					'round': 0,
					'realm_level': current_realm.level
				}
			}

			phenny.say(player.display_level())
			phenny.say(player.display_health())
			phenny.say(monster.display_health())
			if player.ghost:
				etx = '\x02'
				phenny.say("%s %sYou appear to be dead and have spawned as a ghost!" % (player.announce_prepend(), etx))
			phenny.write(('NOTICE', username + " Type !mstats for the monsters full stats or !pstats for your full stats."))
			if monster.fast and randint(1, 10) <= 8: # 80% chance of suprise attack for 'fast' creatures
				phenny.say("%s The %s surprises you with an attack!" % (monster.announce_prepend(), monster.name))
				monsters_choice = monster.choose_attack(current_realm.id)
				if monsters_choice == 'run':
					do_monster_run(phenny, input.uid)
				else:
					do_monster_attack(phenny, monsters_choice, input.uid)
			if in_fight_quiet(input.uid):
				player.can_attack = True
				player.attack_options(phenny, username)
				# player.attack_timer = Timer(ATTACK_TIMEOUT, force_attack, [phenny, input])
				# player.attack_timer.start()
explore.commands = ['explore', 'hunt']
explore.priority = 'low'
explore.example = '!explore'


######################
# IN-FIGHT FUNCTIONS #
######################

def player_stats(phenny, input):
	if in_fight_quiet(input.uid):
		player = ongoing_fights[input.uid]['player']
		player.display_full_stats(phenny)
	else:
		player = p.create_player(phenny, input.uid, input.nick)
		player.display_full_stats(phenny)
		del player
player_stats.commands = ['pstats', 'playerstats', 'mystats', 'u']
player_stats.priority = 'medium'
player_stats.example = '!pstats'

def monster_stats(phenny, input):
	if in_fight(phenny, input.uid):
		monster = ongoing_fights[input.uid]['monster']
		monster.display_full_stats(phenny)
monster_stats.commands = ['mstats', 'cstats', 'monsterstats', 'creaturestats', 'mu']
monster_stats.priority = 'medium'
monster_stats.example = '!mstats'

# The command for when a user uses !run
def run(phenny, input):
	if in_fight(phenny, input.uid):
		player = ongoing_fights[input.uid]['player']
		if player.can_attack:
			player.can_attack = False
			do_round_moves(phenny, input, 'run')
		else:
			phenny.write(('NOTICE', input.nick + " It is not your turn to attack."))
run.commands = ['run']
run.priority = 'high'
run.example = '!run'

# The command for when a user uses !attack #
def attack(phenny, input):
	args = check_args(phenny, input.group(0))
	if args and in_fight(phenny, input.uid):
		attack_id = args[0]
		if not attack_id.isdigit():	
			phenny.write(('NOTICE', input.nick + " You did not enter a valid attack #. Note that this should be numeric."))
			return False
		else:
			attack_id = int(attack_id)

		player = ongoing_fights[input.uid]['player']
		if attack_id > 0 and attack_id <= len(player.attacks) and player.attacks[attack_id - 1]:
			attack_id -= 1
			attack = player.attacks[attack_id]
			if attack.uses >= attack.max_uses:
				phenny.write(('NOTICE', input.nick + " You have used that attack too many times. Try a new one."))
				return False
			if attack.realm_requirement > 0 and current_realm.id != attack.realm_requirement:
				phenny.write(('NOTICE', input.nick + " That attack cannot be used in this realm! It will only work in the %s realm." % attack.realm_requirement_name))
				return False
			if player.can_attack:
				player.can_attack = False
				if player.attack_timer and player.attack_timer.is_alive():
					player.attack_timer.cancel()
					player.attack_timer = False
				do_round_moves(phenny, input, attack)
			else:
				phenny.write(('NOTICE', input.nick + " It is not your turn to attack."))
		else:
			phenny.write(('NOTICE', input.nick + " That is not a valid attack #."))
attack.commands = ['attack']
attack.priority = 'high'
attack.example = '!attack 1'

# If a user doesn't choose an attack in time, run this function
def force_attack(phenny, input):
	if in_fight_quiet(input.uid):
		player = ongoing_fights[input.uid]['player']
		if player.can_attack:
			player.can_attack = False
			attack = player.choose_auto_attack(current_realm.id)
			phenny.write(('NOTICE', input.nick + " You took too long to choose an attack and a random attack is now being chosen for you."))
			if player.attack_timer and player.attack_timer.is_alive():
					player.attack_timer.cancel()
					player.attack_timer = False
			do_round_moves(phenny, input, attack)

def item(phenny, input):
	args = check_args(phenny, input.group(0))
	if args:
		if in_fight(phenny, input.uid):
			item_id = args[0]
			if not item_id.isdigit():	
				phenny.write(('NOTICE', input.nick + " You did not enter a valid item #. Note that this should be numeric."))
				return False
			else:
				item_id = int(item_id)

			player = ongoing_fights[input.uid]['player']
			if item_id > 0 and item_id in player.items.keys() and player.items[item_id]:
				attack = player.items[item_id]
				if 'Embargo' in player.effects:
					phenny.write(('NOTICE', input.nick + " You have been blocked from using items!"))
					return False
				if attack.realm_requirement > 0 and current_realm.id != attack.realm_requirement:
					phenny.write(('NOTICE', input.nick + " That item cannot be used in this realm! It will only work in the %s realm." % attack.realm_requirement_name))
					return False
				if player.can_attack:
					player.can_attack = False
					if player.attack_timer and player.attack_timer.is_alive():
						player.attack_timer.cancel()
						player.attack_timer = False

					item_can_use = phenny.callGazelleApi({'action': 'fightCheckItem', 'userid': player.uid, 'slotid': item_id, 'attackid': attack.id})
					if not item_can_use or 'status' not in item_can_use or item_can_use['status'] == "error":
						if not item_can_use:
							phenny.write(('NOTICE', input.nick + " An error occurred."))
						elif item_can_use['status'] == "error":
							phenny.write(('NOTICE', input.nick + " Error: " + item_can_use['error']))
						# player.attack_timer = Timer(ATTACK_TIMEOUT, force_attack, [phenny, input])
						# player.attack_timer.start()
						player.can_attack = True
					else:
						attack.item_id = item_id
						do_round_moves(phenny, input, attack)
				else:
					phenny.write(('NOTICE', input.nick + " It is not your turn to attack."))
			else:
				phenny.write(('NOTICE', input.nick + " That is not a valid item #."))
	else:
		items(phenny, input)
item.commands = ['item']
item.priority = 'high'
item.example = '!item 1'

def items(phenny, input):
	if in_fight(phenny, input.uid):
		player = ongoing_fights[input.uid]['player']
		player.item_options(phenny, input.nick)
items.commands = ['items']
items.priority = 'medium'
items.example = '!items'



############################
# IN-FIGHT - PROCESS MOVES #
############################

# Once both the player and the monsters moves have been logged, perform attacks/runs in correct order then any status effects
def do_round_moves(phenny, input, player_attack):
	if in_fight_quiet(input.uid):
		ongoing_fights[input.uid]['data']['round'] += 1
		player = ongoing_fights[input.uid]['player']
		monster = ongoing_fights[input.uid]['monster']

		cur_round = ongoing_fights[input.uid]['data']['round']
		#Expire secondary effects
		player.expire_effects(phenny, cur_round)
		monster.expire_effects(phenny, cur_round)

		if 'Sleep' in player.effects:
			player_attack = 'sleep'
		players_choice = player_attack
		if 'Sleep' in monster.effects:
			monsters_choice = 'sleep'
		else:
			monsters_choice = monster.choose_attack(current_realm.id)

		players_attack_priority = get_attack_priority(players_choice)
		monsters_attack_priority = get_attack_priority(monsters_choice)

		#Expire buffs
		player.expire_buffs(phenny, cur_round)
		monster.expire_buffs(phenny, cur_round)

		if players_attack_priority > monsters_attack_priority:
			do_player_first(phenny, input, players_choice, monsters_choice)
		elif monsters_attack_priority > players_attack_priority:
			do_monster_first(phenny, input, players_choice, monsters_choice)
		else:
			if player.stats['speed'] > monster.stats['speed']:
				do_player_first(phenny, input, players_choice, monsters_choice)
			elif monster.stats['speed'] > player.stats['speed']:
				do_monster_first(phenny, input, players_choice, monsters_choice)
			else:
				if randint(0, 1) == 1:
					do_player_first(phenny, input, players_choice, monsters_choice)
				else:
					do_monster_first(phenny, input, players_choice, monsters_choice)

		if in_fight_quiet(input.uid):
			do_effects_damage(phenny, input.uid)

		if in_fight_quiet(input.uid):
			phenny.say(player.display_health())
			phenny.say(monster.display_health())
			player.attack_options(phenny, input.nick)
			# player.attack_timer = Timer(ATTACK_TIMEOUT, force_attack, [phenny, input])
			# player.attack_timer.start()
			player.can_attack = True

# Perform attacks/runs with the player going first. Called by the do_round_moves function.
def do_player_first(phenny, input, players_choice, monsters_choice):
	if players_choice == 'run':
		do_player_run(phenny, input.uid, input.nick)
	elif players_choice == 'sleep':
		do_player_sleep(phenny, input.uid)
	else:
		do_player_attack(phenny, players_choice, input.uid, input.nick, True)

	if in_fight_quiet(input.uid):
		monster = ongoing_fights[input.uid]['monster']
		if 'Sleep' in monster.effects:
			monsters_choice = 'sleep'
			
		if 'Flinching' in monster.effects:
			phenny.say("%s The %s flinched and couldn't attack!" % (monster.announce_prepend(), monster.name))
			del monster.effects['Flinching']
			if 'Confusion' in monster.effects:
				monster.effects['Confusion'] += 1
			return False

		if monsters_choice == 'run':
			do_monster_run(phenny, input.uid)
		elif monsters_choice == 'sleep':
			do_monster_sleep(phenny, input.uid)
		else:
			do_monster_attack(phenny, monsters_choice, input.uid)

# Perform attacks/runs with the monster going first. Called by the do_round_moves function.
def do_monster_first(phenny, input, players_choice, monsters_choice):
	if monsters_choice == 'run':
		do_monster_run(phenny, input.uid)
	elif monsters_choice == 'sleep':
		do_monster_sleep(phenny, input.uid)
	else:
		do_monster_attack(phenny, monsters_choice, input.uid, True)

	if in_fight_quiet(input.uid):
		player = ongoing_fights[input.uid]['player']
		if 'Sleep' in player.effects:
			players_choice = 'sleep'

		if 'Flinching' in player.effects:
			phenny.say("%s You flinched and couldn't attack!" % (player.announce_prepend()))
			del player.effects['Flinching']
			if 'Confusion' in player.effects:
				player.effects['Confusion'] += 1
			return False
			
		if players_choice == 'run':
			do_player_run(phenny, input.uid, input.nick)
		elif players_choice == 'sleep':
			do_player_sleep(phenny, input.uid)
		else:
			do_player_attack(phenny, players_choice, input.uid, input.nick)

# Execute the run command. Called by the do_round_moves function.
def do_player_run(phenny, userid, username):
	if in_fight_quiet(userid):
		player = ongoing_fights[userid]['player']
		monster = ongoing_fights[userid]['monster']

		if 'Confusion' in player.effects:
			player.effects['Confusion'] += 1

		if 'CantEscape' in player.effects:
			phenny.say("%s You were blocked and cannot run!" % player.announce_prepend())
			return False

		success = player.run(monster)
		if success:
			phenny.say("%s %s ran from the %s!" % (player.announce_prepend(), player.site_username, monster.name))
			end_fight(phenny, userid)
		else:
			phenny.say("%s %s attempted to run from the %s but failed!" % (player.announce_prepend(), player.site_username, monster.name))

def do_monster_run(phenny, userid):
	if in_fight_quiet(userid):
		player = ongoing_fights[userid]['player']
		monster = ongoing_fights[userid]['monster']
		success = monster.run(player)
		if success:
			phenny.say("%s The %s ran from you!" % (monster.announce_prepend(), monster.name))
			end_fight(phenny, userid)
		else:
			phenny.say("%s The %s attempted to run from you but failed!" % (monster.announce_prepend(), monster.name))
			if 'Confusion' in monster.effects:
				monster.effects['Confusion'] += 1

def do_player_sleep(phenny, userid):
	if in_fight_quiet(userid):
		player = ongoing_fights[userid]['player']
		phenny.say("%s %s is fast asleep and cannot attack. ZzzZZzzZZzz..." % (player.announce_prepend(), player.site_username))
		if 'Confusion' in player.effects:
			player.effects['Confusion'] += 1

def do_monster_sleep(phenny, userid):
	if in_fight_quiet(userid):
		monster = ongoing_fights[userid]['monster']
		phenny.say("%s The %s is fast asleep and cannot attack. ZzzZZzzZZzz..." % (monster.announce_prepend(), monster.name))
		if 'Confusion' in monster.effects:
			monster.effects['Confusion'] += 1

# Execute an attack. Called by the do_round_moves function.
def do_player_attack(phenny, attack, userid, username, first_turn = False):
	player = ongoing_fights[userid]['player']
	monster = ongoing_fights[userid]['monster']

	if 'Freezing' in player.effects:
		if randint(1,5) != 1:
			phenny.say("%s %s is frozen solid and cannot attack!" % (player.announce_prepend(), player.site_username))
			if 'Confusion' in player.effects:
				player.effects['Confusion'] += 1
			return False
		else:
			phenny.say("%s %s is frozen solid... but breaks free!" % (player.announce_prepend(), player.site_username))
			del player.effects['Freezing']

	if attack.is_item:
		item_id = attack.item_id
		item_use = phenny.callGazelleApi({'action': 'fightUseItem', 'userid': player.uid, 'slotid': item_id})
		if not item_use or 'status' not in item_use:
			phenny.write(('NOTICE', username + " An error occurred trying to use that item."))
			attack = player.choose_auto_attack(current_realm.get_id())
			phenny.say("%s %s failed to use their item. Used %s instead." % (player.announce_prepend(), player.site_username, attack.name))
			attack.uses += 1
		elif item_use['status'] == "error":
			phenny.write(('NOTICE', username + " Error: " + item_use['error']))
			attack = player.choose_auto_attack(current_realm.get_id())
			phenny.say("%s %s failed to use their item. Used %s instead." % (player.announce_prepend(), player.site_username, attack.name))
			attack.uses += 1
		elif item_use['status'] == 'ok':
			phenny.say("%s %s used %s (item)." % (player.announce_prepend(), player.site_username, attack.name))
			del player.items[item_id]
	else:
		phenny.say("%s %s used %s." % (player.announce_prepend(), player.site_username, attack.name))
		attack.uses += 1

	if 'Confusion' in player.effects and randint(1,3) == 1:
		player.attack_self_confused(phenny, monster)
		if player.health <= 0 or monster.health <= 0:
			end_fight(phenny, userid)
		return False

	if attack_hit(attack, userid, 'monster'):
		cur_round = ongoing_fights[userid]['data']['round']
		player.attack_monster(phenny, cur_round, attack, monster, first_turn)
		if player.health <= 0 or monster.health <= 0:
			end_fight(phenny, userid)
	else:
		phenny.say("%s %s's attack missed!" % (player.announce_prepend(), player.site_username))

def do_monster_attack(phenny, attack, userid, first_turn = False):
	player = ongoing_fights[userid]['player']
	monster = ongoing_fights[userid]['monster']

	if 'Freezing' in monster.effects:
		if randint(1,5) != 1:
			phenny.say("%s The %s is frozen solid and cannot attack!" % (monster.announce_prepend(), monster.name))
			if 'Confusion' in monster.effects:
				monster.effects['Confusion'] += 1
			return False
		else:
			phenny.say("%s The %s is frozen solid... but breaks free!" % (monster.announce_prepend(), monster.name))
			del monster.effects['Freezing']

	phenny.say("%s The %s used %s." % (monster.announce_prepend(), monster.name, attack.name))
	attack.uses += 1

	if 'Confusion' in monster.effects and randint(1,3) == 1:
		monster.attack_self_confused(phenny, player)
		if player.health <= 0 or monster.health <= 0:
			end_fight(phenny, userid)
		return False

	if attack_hit(attack, userid, 'player'):
		cur_round = ongoing_fights[userid]['data']['round']
		monster.attack_player(phenny, cur_round, attack, player, first_turn)
		if player.health <= 0 or monster.health <= 0:
			end_fight(phenny, userid)
	else:
		phenny.say("%s The %s's attack missed!" % (monster.announce_prepend(), monster.name))

# Apply status effects
def do_effects_damage(phenny, userid):
	player = ongoing_fights[userid]['player']
	monster = ongoing_fights[userid]['monster']

	if in_fight_quiet(userid):
		if 'Poison' in player.effects or 'Burn' in player.effects:
			eighth_health = max(floor(player.max_health / 8), 1)
			player.health -= eighth_health
			if player.health <= 0:
				player.health = 0
			if 'Poison' in player.effects:
				phenny.say('%s You were hurt by poison! You took %d damage.' % (player.announce_prepend(), eighth_health))
			else:
				phenny.say('%s You were hurt by your burn! You took %d damage.' % (player.announce_prepend(), eighth_health))
			if player.health <= 0:
				end_fight(phenny, userid)
		if 'Poison' in monster.effects or 'Burn' in monster.effects:
			eighth_health = max(floor(monster.max_health / 8), 1)
			monster.health -= eighth_health
			if monster.health <= 0:
				monster.health = 0
			if 'Poison' in monster.effects:
				phenny.say('%s The %s is hurt by poison! It took %d damage.' % (monster.announce_prepend(), monster.name, eighth_health))
			else:
				phenny.say('%s The %s is hurt by its burn! It took %d damage.' % (monster.announce_prepend(), monster.name, eighth_health))
			if monster.health <= 0:
				end_fight(phenny, userid)
		
		if 'HPLeech' in player.effects:
			eighth_health = max(floor(player.max_health / 8), 1)
			player.health -= eighth_health
			if player.health < 0:
				player.health = 0
			if (monster.health + eighth_health) > monster.max_health:
				monster.health = monster.max_health
			else:
				monster.health += eighth_health
			phenny.say('%s Your health was sapped! The %s stole %d HP from you.' % (monster.announce_prepend(), monster.name, eighth_health))
			if player.health <= 0:
				end_fight(phenny, userid)
		if 'HPLeech' in monster.effects:
			eighth_health = max(floor(monster.max_health / 8), 1)
			monster.health -= eighth_health
			if monster.health < 0:
				monster.health = 0
			if (player.health + eighth_health) > player.max_health:
				player.health = player.max_health
			else:
				player.health += eighth_health
			phenny.say('%s You sapped the %s\'s health! You stole %d HP from it.' % (player.announce_prepend(), monster.name, eighth_health))
			if monster.health <= 0:
				end_fight(phenny, userid)

		if player.health <= 0 or monster.health <= 0:
			end_fight(phenny, userid)


###################
# BASIC FUNCTIONS #
################### 

# Cycles to a new realm
def create_new_realm(phenny):
	global current_realm, realm_switch_timer

	current_realmid = False
	if current_realm:
		current_realmid = current_realm.get_id()
	if lock_realm == False or current_realmid == False:
		new_realm_info = phenny.callGazelleApi({'action': 'randomRealm', 'current_realm': current_realmid})
		if not new_realm_info or 'status' not in new_realm_info or new_realm_info['status'] == "error":
			realm_switch_timer.cancel()
			realm_switch_timer = Timer(REALM_CYCLE_RETRY, create_new_realm, [phenny])
			realm_switch_timer.start()
			return False
		else:
			current_realm = False
			current_realm = fight.realm.create(new_realm_info['ID'], new_realm_info['Name'], new_realm_info['Level'], new_realm_info['HuntCost'], new_realm_info['Monsters'])
			current_realm.announce(phenny)
	else:
		phenny.say("The guide tried to move to a new realm but was blocked by staff!")
	realm_switch_timer.cancel()
	realm_switch_timer = Timer(REALM_CYCLE, create_new_realm, [phenny])
	realm_switch_timer.start()

# Let staff manually set a new realm or users if the realm is open
def set_new_realm(phenny, mod, realmid):
	global current_realm, game_started, realm_switch_timer
	
	if realmid.isdigit():
		if mod or open_realm:
			if mod:
				new_realm_info = phenny.callGazelleApi({'action': 'getRealm', 'realmid': realmid})
			else:
				new_realm_info = phenny.callGazelleApi({'action': 'getRealm', 'realmid': realmid, 'enabledonly': 'true'})
			if not new_realm_info or 'status' not in new_realm_info or new_realm_info['status'] == "error":
				return False
			if new_realm_info['status'] == 'ok':
				game_started = True
				current_realm = False
				current_realm = fight.realm.create(realmid, new_realm_info['Name'], new_realm_info['Level'], new_realm_info['HuntCost'], new_realm_info['Monsters'])
				current_realm.announce(phenny)
				realm_switch_timer.cancel()
				realm_switch_timer = Timer(REALM_CYCLE, create_new_realm, [phenny])
				realm_switch_timer.start()
			else:
				phenny.say(new_realm_info['error'])
		else:
			phenny.say("You do not have permission to use this command.")
	else:
		phenny.say("Error. The input should be a realm ID.")

# End the fight
def end_fight(phenny, userid):
	if in_fight_quiet(userid):
		player = ongoing_fights[userid]['player']
		monster = ongoing_fights[userid]['monster']
		etx = '\x02'
		if player.health <= 0 and monster.health <= 0:
			phenny.say("%sBoth you and the %s died! The battle is a draw." % (etx, monster.name))
		elif player.health <= 0:
			phenny.say("%sYou died! You lost the battle!" % etx)
		elif monster.health <= 0:
			phenny.say("%sThe %s died! You win the battle!" % (etx, monster.name))

		if player.health > 0 and monster.health <= 0: # if player won
			if player.level <= (ongoing_fights[userid]['data']['realm_level'] + 30):
				drops = phenny.callGazelleApi({'action': 'fightReward', 'userid': player.uid, 'monsterid': monster.id})
				if not drops or 'status' not in drops or drops['status'] == "error":
					phenny.write(('NOTICE', player.site_username + " An error occurred trying to process your rewards."))
				elif drops and 'msg' in drops:
					phenny.say("%s%s" % (etx, drops['msg']))
			experience = player.calculate_experience_gain(monster)
			phenny.say("%sYou gained %d experience." % (etx, experience))
			new_level_response = phenny.callGazelleApi({'userid': userid, 'experience': experience, 'action': 'fightAddExperience'})

			if not new_level_response or 'status' not in new_level_response or new_level_response['status'] == "error":
				phenny.write(('NOTICE', player.site_username + " An error occurred updating your XP."))
			elif new_level_response['status'] == 'ok' and 'msg' in new_level_response:
				new_level = new_level_response['msg']
				if new_level > player.level:
					phenny.say("%sLevel up! You grew to level %d!" % (etx, new_level))

		if player.health <= 0: # if player lost
			lose_response = phenny.callGazelleApi({'userid': userid, 'monsterid': monster.id, 'action': 'fightLosses'})
			if not lose_response or 'status' not in lose_response or lose_response['status'] == "error":
				phenny.write(('NOTICE', player.site_username + " An error occurred trying to process your losses."))
			elif lose_response['status'] == 'ok' and 'msg' in lose_response:
				phenny.say("%s%s" % (etx, lose_response['msg']))
		if not player.ghost:
			phenny.callGazelleApi({'userid': userid, 'health': player.health, 'action': 'fightSetHealth'})
		phenny.say("The fight between %s and the %s has ended." % (player.site_username, monster.name))
		phenny.say("==========================================")
		current_realm.info(phenny)
		del ongoing_fights[userid]
		# TODO: Add timer for 2 minute cooldown


####################
# HELPER FUNCTIONS #
#################### 

# Check if the user is in a fight
def in_fight(phenny, userid):
	if not game_started:
		phenny.say("There is currently no adventure in progress. Use !start to get started.") 
		return False
	elif not userid in ongoing_fights or not ongoing_fights[userid]:
		phenny.say("You can't use that command as you are not currently in a fight. To attempt a hunt, type !explore") 
		return False
	else:
		return True

def in_fight_quiet(userid):
	if not game_started:
		return False
	elif not userid in ongoing_fights or not ongoing_fights[userid]:
		return False
	else:
		return True

# Returns an attacks priority level (between 0 and 255)
def get_attack_priority(attack):
	if attack == 'run':
		return 150
	elif attack == 'sleep':
		return 255
	else:
		return attack.priority

# Check if attack will hit
# target = 'monster' or 'player'
def attack_hit(attack, userid, target):
	if attack.accuracy >= 99:
		return True

	if target == 'monster':
		attacker = ongoing_fights[userid]['player']
		target = ongoing_fights[userid]['monster']
	else:
		attacker = ongoing_fights[userid]['monster']
		target = ongoing_fights[userid]['player']
	speed_diff = attacker.stats['speed'] - target.stats['speed']
	speed_diff = min(max(speed_diff, -10), 10) # cap at -10/+10
	test = attack.accuracy + speed_diff

	if randint(0, 99) < test:
		if 'Blindness' in attacker.effects:
			if randint(1,4) == 1:
				return True
			else:
				return False
		else:
			return True
	else:
		return False

# Check amount of args is correct, returns all args or false if incorrect amount
def check_args(phenny, args):
    args = args.split()
    cmd = args[0][1:]
    args.pop(0)
    if len(args) < arguments[cmd]:
        phenny.say(help[cmd])
        return False
    else:
        return args