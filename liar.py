# gamemaster
import copy
import math
import random
import logging

from helpers import Bid
from helpers import InvalidBid
from helpers import get_die_freq


def getdie(qty, sides):
    die = []
    for i in range(qty):
        die.append(random.randint(1, sides))
    return die


def evaluate_bid(game_rules, bid, last_bid, all_die, value_locked=False):
    # we evaluate that the bid is valid
    # and if so, whether it was correct (win or lose)
    # we must take account of the state of '1s', wilds, quantity_locked if player opens bid with only one die
    # win - True, lose - False, continue - None, error - InvalidBid

    if bid.call == 'bid':
        # otherwise they 'raised' the bid - qty and value have to be greater than the last bid
        if last_bid is None:
            return None

        if value_locked and bid.value != last_bid.value:
            raise InvalidBid('invalid bid - value is locked and must be %s' % last_bid.value)

        if game_rules.wilds_lock:
            if last_bid.value == 1:
                # last value was a wild, so you must continue or double
                if ((bid.value == 1 and bid.quantity > last_bid.quantity)
                    or (bid.value > 1 and bid.quantity >= (2 * last_bid.quantity + 1))):
                    return None
                else:
                    raise InvalidBid('wilds: you must bid on ones, or double+1 quantity')

            if bid.value == 1 and last_bid.value != 1:
                # changed to a wild, must have halved the quantity
                if bid.quantity == int(math.ceil(last_bid.quantity / 2.0)):
                    return None
                else:
                    raise InvalidBid('wilds: to bid on ones, you must halve quantity')

        if ((bid.value >= last_bid.value)
            and (bid.quantity >= last_bid.quantity)
            and ((bid.value > last_bid.value) or (bid.quantity > last_bid.quantity))):
            return None
        else:
            raise InvalidBid('qty or val too low')
    else:
        # LIAR!
        # get die frequency
        if last_bid is None:
            raise InvalidBid('cannot call exact or liar as the first bid')
        freq = get_die_freq(all_die, ones_as_value=(last_bid.value if game_rules.wilds else False))
        # handle exact and liar calls
        if bid.call == 'exact' and game_rules.exact:
            return freq.get(last_bid.value) == last_bid.quantity
        elif bid.call == 'liar':
            return freq.get(last_bid.value) < last_bid.quantity
        else:
            raise InvalidBid('invalid call type %s' % bid.call)


def make_player_first(player_list, player):
    player_list.insert(0, player_list.pop(player_list.index(player)))


class GameRules(object):
    def __init__(self, exact=False, wilds=False, wilds_lock=False, value_lock=False, starting_die=5, die_sides=6,
                 bestof=False):
        # in 'exact', you can call 'exact' if you think the previous bid was spot-on. in this game, everyone else loses a die.
        # wilds - whether 1s are different to all other numbers, in that they assume the number of the bid
        # wilds_lock - whether calling 'wilds' i.e. three ones locks players into calling ones, or they must double+1 e.g. seven fives
        #    (the reverse is also true - you can halve quantity and lock in to ones)
        # value_lock - whether players that have reached a single die cause their initial bid to lock the value for the rest of the round
        # starting die - how many die each player has to start the game
        # die_sides - how many sides the die have
        # bestof - in bestof, the match is won when one player has won more than games/nplayers
        self.exact = exact
        self.wilds = wilds
        self.wilds_lock = wilds_lock
        self.starting_die = starting_die
        self.die_sides = die_sides
        self.value_lock = value_lock
        self.bestof = bestof

    def __str__(self):
        return str(self.__dict__)


class Match(object):
    """
    this does all the work of managing the game, rather like a Game Master (GM)
    """

    def __init__(self, rules, games=3, loglevel=20):
        self.rules = rules
        self.games = games
        self.players = []
        self.results = []
        self.in_progress = False
        logging.basicConfig(level=loglevel)
        self.log = logging.getLogger('GM')

    def addPlayer(self, player):
        if not self.in_progress:
            self.players.append(player)

    def run(self):
        # begin the loops
        # match
        #  games (winner is last one with die)
        #   rounds (of die throwing)
        #    bids (raising, liar etc)
        self.in_progress = True

        self.player_count = len(self.players)
        self.bestof_target = int(math.ceil(self.games / float(self.player_count)))

        player_stats = {}
        for player in self.players:
            player_stats[player.name] = {None: 0, True: 0, False: 0, 'derp': 0, 'wins': 0, 'losses': 0}

        self.log.warn('MATCH STARTS. %s GAME(S) WITH %s, RULES %s' % (
            self.games, ['%s' % player for player in self.players], self.rules))

        if self.rules.bestof:
            self.log.info('BEST OF %s: NEED %s TO WIN' % (self.games, self.bestof_target))

        for game in range(self.games):
            self.log.info("GAME STARTED")

            game_stats = {None: 0, True: 0, False: 0, 'derp': 0, 'wins': 0, 'losses': 0}
            player_die = {}
            player_die_count = {}

            for player in self.players:
                player_die_count[player.name] = self.rules.starting_die
                player_die[player.name] = []

            # start the players in random order
            random.shuffle(self.players)
            for player in self.players:
                player.new_game(self.players, self.rules)

            while True:
                # each round we throw the die
                all_die = []
                active_players = []
                for player in self.players:
                    die_count = player_die_count[player.name]
                    # is this player out?
                    if die_count <= 0:
                        continue
                    die = getdie(die_count, self.rules.die_sides)
                    player_die[player.name] = die
                    # list of all die, for convenience
                    all_die += die
                    player.new_round(copy.copy(die), copy.deepcopy(player_die_count))
                    active_players.append(player)

                if len(active_players) <= 1:
                    # we have a winner!
                    self.log.info("GAME WON BY %s, CONGRATULATIONS!" % active_players[0].name)
                    player_stats[active_players[0].name]['wins'] += 1
                    for player in self.players:
                        if player.name != active_players[0].name:
                            player_stats[player.name]['losses'] += 1
                    break

                # apply the value lock if this player has only one die
                value_lock = player_die_count[active_players[0].name] == 1 and self.rules.value_lock

                # within a round, we can go around the 'table' many times (bidding from 1...inf until liar!), so loop players forever
                lastbid = None
                outcome = None
                last_player = None
                while outcome is None:
                    for player in active_players:
                        # some players are allowed as many invalid bid attempts as they like, so we must loop
                        while True:
                            bid = player.get_bid(lastbid, value_lock=value_lock)
                            try:
                                outcome = evaluate_bid(self.rules, bid, lastbid, all_die, value_lock)
                                break
                            except InvalidBid, e:
                                self.log.debug('invalid bid, %s, you ought to lose a die for that!' % e)
                                player_stats[player.name]['derp'] += 1
                                game_stats['derp'] += 1
                                outcome = False
                                if not player.allow_retries:
                                    break
                        player_stats[player.name][outcome] += 1
                        game_stats[outcome] += 1
                        if outcome is None:
                            # bid was raised, so we continue bidding
                            lastbid = bid
                            last_player = player
                            self.log.debug('%s %s' % (player.name, bid))
                            continue
                        else:
                            # player ended this round (we have to reveal the dice and will need another throw)
                            break
                # ok we got an outcome!
                self.log.debug(
                    '%s called %s %s and the die were: %s' % (player.name, last_player.name, bid, sorted(all_die)))
                if outcome:
                    if bid.call == 'exact':
                        self.log.debug('%s called EXACT and was SPOT ON!' % player.name)
                        make_player_first(self.players, player)
                        # all other players lose a die!
                        for all_other in active_players:
                            if all_other.name != player.name:
                                player_die_count[all_other.name] -= 1
                    else:
                        self.log.debug(
                            '%s called LIE and was right!, %s is a liar...' % (player.name, last_player.name))
                        # previous player was lying!
                        player_die_count[last_player.name] -= 1
                        make_player_first(self.players, last_player)
                else:
                    self.log.debug('%s called %s and was wrong!' % (player.name, bid))
                    # this player got it wrong and loses a die!
                    player_die_count[player.name] -= 1
                    make_player_first(self.players, player)

            self.log.info("GAME FINISHED %s" % game_stats)

            if self.rules.bestof:
                bestof_done = False
                for player in self.players:
                    if player_stats[player.name]['wins'] >= self.bestof_target:
                        self.log.warn("MATCH FINISHED - %s WON BEST OF %s WITH %s of %s GAMES" % (
                            player.name,
                            self.games,
                            player_stats[player.name]['wins'],
                            player_stats[player.name]['wins'] + player_stats[player.name]['losses'],
                        ))
                        bestof_done = True
                        break
                if bestof_done:
                    break

        for player in self.players:
            self.log.warn("%s %s" % (player.name, player_stats[player.name]))
        self.in_progress = False
