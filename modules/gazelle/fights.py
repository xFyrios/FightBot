#!/usr/bin/env python

import fight.player as p, fight.monster as m, fight.realm
from collections import OrderedDict
from random import randint
from math import floor
from threading import Timer

REALM_CYCLE = 60 * 60 * 6  # How often to cycle to a new realm (6 hours)

game_started = False  # set to true after !start has been called
current_realm = False  # holds the realm object
lock_realm = False # if the realm has been blocked from auto cycling to a new one
ongoing_fights = {} # holds the player and monster objects for ongoing fights. 
					# The key for each fight is the users id, the value is another dictionary 
					# with Player under key 'player', and Monster under 'monster':  {userid: {'player': Player, 'monster': Monster, 'data': {}}}
					# 'data' can hold miscellaneous data such as the round #

arguments = {'start': 0, 'setrealm': 1, 'realmlock': 0, 'realmunlock': 0, 'info': 0, 'explore': 0, 'stats': 0, 'run': 0, 'attack': 1,}
help = OrderedDict([('start', "If adventuring has not already begun, use !start to get the bot going."),
					('info', "To get info on the current realm you are exploring, use the !info or !status command."),
					('explore', "To attempt a hunt, use the command !explore or !hunt."),
					('pstats', "Show your full player stats with !stats. Only works when you are in a fight. Alternative: !mystats or !u"),
					('mstats', "Show the monsters full stats (that you are versing) with !mstats. Only works when you are in a fight. Alternative: !cstats or !mu"),
					('attack', "To attack a creature use the command !attack #, where # is the number of the attack. Only works when you are in a fight."),
					('run', "Attempt to !run from a monster. Only works when you are in a fight and it is your turn to attack."),
					('setrealm', "To change to a new realm, use !setrealm realmid. Only useable by mods."),
					('realmlock', "To stop the realm from changing once every %d hours, use !realmlock. To unlock it again, use !realmunlock. Only useable by mods." % REALM_CYCLE)])

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
        phenny.say("For more info on a command, type '!fighthelp cmd' where cmd is the name of the command you want help for.")
    else:
        cmd = input.group(2)
        if cmd in help.keys():
            phenny.say(help[cmd])
        else:
            phenny.say('That command does not exist.')
            phenny.say('Commands I recognize include: ' + ', '.join(help.keys()))
fight_help.commands = ['fighthelp']
fight_help.priority = 'low'
fight_help.example = '!fighthelp info'

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


# Set a new realm manually
def set_realm(phenny, input):
	args = check_args(phenny, input.group(0))
	if args:
		realmid = args[0]
		set_new_realm(phenny, input.mod, realmid)
set_realm.commands = ['setrealm']
set_realm.priority = 'low'
set_realm.example = '!realm 1'

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
	elif input.uid in ongoing_fights.keys():
		phenny.say("You can't keep exploring... you are already in a fight!") 
	elif input.uid:
		userid = input.uid
		username = input.nick
		monster_id = current_realm.explore(phenny, userid, username)
		if monster_id:
			# Create the player and monster objects, add them to the ongoing_fights dictionary
			print 'New Fight!'
			player = p.create_player(phenny, userid, username)
			print u'%s' % player
			monster = m.create_monster(phenny, monster_id, username)
			monster.announce(phenny)
			print u'%s' % monster
			ongoing_fights[input.uid] = {
				'player': player,
				'monster': monster,
				'data': {
					'round': 0
				}
			}

			phenny.say(player.display_level())
			phenny.say(player.display_health())
			phenny.write(('NOTICE', username + " Type !mstats for the monsters full stats or !pstats for your full stats."))
			if monster.fast and randint(1, 10) <= 8: # 80% chance of suprise attack for 'fast' creatures
				phenny.say("%s The %s surprises you with an attack!" % (monster.announce_prepend(), monster.name))
				monsters_choice = monster.choose_attack()
				if monsters_choice == 'run':
					do_monster_run(phenny, input.uid)
				else:
					do_monster_attack(phenny, monsters_choice, input.uid)
			if in_fight_quiet(input.uid):
				player.can_attack = True
				player.attack_options(phenny, username)
explore.commands = ['explore', 'hunt']
explore.priority = 'low'
explore.example = '!explore'


######################
# IN-FIGHT FUNCTIONS #
######################

def player_stats(phenny, input):
	if in_fight(phenny, input.uid):
		player = ongoing_fights[input.uid]['player']
		player.display_full_stats(phenny)
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
				do_round_moves(phenny, input, attack_id)
			else:
				phenny.write(('NOTICE', input.nick + " It is not your turn to attack."))
		else:
			phenny.write(('NOTICE', input.nick + " That is not a valid attack #."))
attack.commands = ['attack']
attack.priority = 'high'
attack.example = '!attack 1'

############################
# IN-FIGHT - PROCESS MOVES #
############################

# Once both the player and the monsters moves have been logged, perform attacks/runs in correct order then any status effects
def do_round_moves(phenny, input, player_attack):
	if in_fight_quiet(input.uid):
		ongoing_fights[input.uid]['data']['round'] += 1
		player = ongoing_fights[input.uid]['player']
		monster = ongoing_fights[input.uid]['monster']
		players_choice = player_attack
		monsters_choice = monster.choose_attack()
		players_attack_priority = get_attack_priority('run' if players_choice == 'run' else player.attacks[players_choice])
		monsters_attack_priority = get_attack_priority(monsters_choice)

		#Expire buffs and secondary effects
		cur_round = ongoing_fights[input.uid]['data']['round']
		player.expire_buffs(phenny, cur_round)
		monster.expire_buffs(phenny, cur_round)
		player.expire_effects(phenny, cur_round)
		monster.expire_effects(phenny, cur_round)

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

		#TODO: After both attacks, apply status effects. Check hp of each creature afterwards to see if dead.
		if in_fight_quiet(input.uid):
			player.attack_options(phenny, input.nick)
			player.can_attack = True

# Perform attacks/runs with the player going first. Called by the do_round_moves function.
def do_player_first(phenny, input, players_choice, monsters_choice):
	if players_choice == 'run':
		do_player_run(phenny, input.uid, input.nick)
	else:
		do_player_attack(phenny, players_choice, input.uid, input.nick)

	if in_fight_quiet(input.uid):
		if monsters_choice == 'run':
			do_monster_run(phenny, input.uid)
		else:
			do_monster_attack(phenny, monsters_choice, input.uid)

# Perform attacks/runs with the monster going first. Called by the do_round_moves function.
def do_monster_first(phenny, input, players_choice, monsters_choice):
	if monsters_choice == 'run':
		do_monster_run(phenny, input.uid)
	else:
		do_monster_attack(phenny, monsters_choice, input.uid)

	if in_fight_quiet(input.uid):
		if players_choice == 'run':
			do_player_run(phenny, input.uid, input.nick)
		else:
			do_player_attack(phenny, players_choice, input.uid, input.nick)

# Execute the run command. Called by the do_round_moves function.
def do_player_run(phenny, userid, username):
	if in_fight_quiet(userid):
		player = ongoing_fights[userid]['player']
		monster = ongoing_fights[userid]['monster']
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

# Execute an attack. Called by the do_round_moves function.
def do_player_attack(phenny, attackid, userid, username):
	player = ongoing_fights[userid]['player']
	monster = ongoing_fights[userid]['monster']
	attack = player.attacks[attackid]
	phenny.say("%s %s used %s." % (player.announce_prepend(), player.site_username, attack.name))
	attack.uses += 1

	if attack_hit(attack, userid, 'monster'):
		cur_round = ongoing_fights[userid]['data']['round']
		player.attack_monster(phenny, cur_round, attack, monster)
		etx = '\x02'
		if player.health <= 0:
			phenny.say("%sYou died! You lost the battle!." % etx)
			end_fight(phenny, userid)
		elif monster.health <= 0:
			phenny.say("%sThe %s died! You win the battle!" % (etx, monster.name))
			end_fight(phenny, userid)
	else:
		phenny.say("%s %s's attack missed!" % (player.announce_prepend(), player.site_username))

def do_monster_attack(phenny, attack, userid):
	player = ongoing_fights[userid]['player']
	monster = ongoing_fights[userid]['monster']
	phenny.say("%s The %s used %s." % (monster.announce_prepend(), monster.name, attack.name))
	attack.uses += 1

	if attack_hit(attack, userid, 'player'):
		cur_round = ongoing_fights[userid]['data']['round']
		monster.attack_player(phenny, cur_round, attack, player)
		etx = '\x02'
		if player.health <= 0:
			phenny.say("%sYou died! You lost the battle!." % etx)
			end_fight(phenny, userid)
		elif monster.health <= 0:
			phenny.say("%sThe %s died! You win the battle!" % (etx, monster.name))
			end_fight(phenny, userid)
	else:
		phenny.say("%s The %s's attack missed!" % (monster.announce_prepend(), monster.name))


###################
# BASIC FUNCTIONS #
################### 

# Cycles to a new realm
def create_new_realm(phenny):
	global current_realm

	current_realmid = False
	if current_realm:
		current_realmid = current_realm.get_id()
	if lock_realm == False or current_realmid == False:
		new_realm_info = phenny.callGazelleApi({'action': 'randomRealm', 'current_realm': current_realmid})
		current_realm = False
		current_realm = fight.realm.create(new_realm_info['ID'], new_realm_info['Name'], new_realm_info['Level'], new_realm_info['HuntCost'], new_realm_info['Monsters'])
		current_realm.announce(phenny)
	else:
		phenny.say("The guide tried to move to a new realm but was blocked by staff!")
	Timer(REALM_CYCLE, create_new_realm, [phenny]).start()

# Let staff manually set a new realm
def set_new_realm(phenny, mod, realmid):
	global current_realm, game_started
	
	if realmid.isdigit():
		if mod:
			new_realm_info = phenny.callGazelleApi({'action': 'getRealm', 'realmid': realmid})
			if new_realm_info['status'] == 'ok':
				game_started = True
				current_realm = False
				current_realm = fight.realm.create(realmid, new_realm_info['Name'], new_realm_info['Level'], new_realm_info['HuntCost'], new_realm_info['Monsters'])
				current_realm.announce(phenny)
				Timer(REALM_CYCLE, create_new_realm, [phenny]).start()
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
		if player.health > 0 and monster.health <= 0: # if player won
			experience = player.calculate_experience_gain(monster)
			new_level = floor((player.experience + experience) ** (1. / 3))
			etx = '\x02'
			phenny.say("%sYou gained %d experience." % (etx, experience))
			phenny.callGazelleApi({'userid': userid, 'experience': experience, 'action': 'fightAddExperience'})
			if new_level > player.level:
				phenny.say("%sLevel up! You grew to level %d!" % (etx, new_level))
		phenny.callGazelleApi({'userid': userid, 'health': player.health, 'action': 'fightSetHealth'})
		phenny.say("The fight between %s and the %s has ended." % (player.site_username, monster.name))
		phenny.say("==========================================")
		current_realm.info(phenny)
		del ongoing_fights[userid]
		# TODO: Add timer for 5 minute cooldown


####################
# HELPER FUNCTIONS #
#################### 

# Check if the user is in a fight
def in_fight(phenny, userid):
	if not game_started:
		phenny.say("There is currently no adventure in progress. Use !start to get started.") 
		return False
	elif not userid in ongoing_fights.keys() or not ongoing_fights[userid]:
		phenny.say("You can't use that command as you are not currently in a fight. To attempt a hunt, type !explore") 
		return False
	else:
		return True

def in_fight_quiet(userid):
	if not game_started:
		return False
	elif not userid in ongoing_fights.keys() or not ongoing_fights[userid]:
		return False
	else:
		return True

# Returns an attacks priority level (between 0 and 255)
def get_attack_priority(attack):
	if attack == 'run':
		return 150
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