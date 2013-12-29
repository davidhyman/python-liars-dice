# gamemaster
import copy
import math
import random
import os
import logging

from operator import mul
from fractions import Fraction

def memoize(f):
    """ Memoisation decorator for functions taking one or more arguments. """
    class memodict(dict):
        def __init__(self, f):
            self.f = f
        def __call__(self, *args):
            return self[args]
        def __missing__(self, key):
            ret = self[key] = self.f(*key)
            return ret
    return memodict(f)

class InvalidBid(Exception):
    pass

def getdie(qty, sides):
    die = []
    for i in range(qty):
        die.append(random.randint(1, sides))
    return die
    
def get_die_freq(all_die, ones_as_value=False):
    """
    returns a frequency map of {value: quantity} for the die
    ones_as_values - any ones get replaced with this value during counting
    frequency map has no entries for die with frequency 0
    """
    freq = {}
    for die in all_die:
        if (ones_as_value and die==1):
            die = ones_as_value
        freq.setdefault(die, 0)
        freq[die] += 1
        
    return freq
    
    
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
                or (bid.value > 1 and bid.quantity >= (2*last_bid.quantity + 1))):
                    return None
                else:
                    raise InvalidBid('wilds: you must bid on ones, or double+1 quantity')
            
            if bid.value == 1 and last_bid.value != 1:
                # changed to a wild, must have halved the quantity
                if bid.quantity == int(math.ceil(last_bid.quantity/2.0)):
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
        # get die frequency
        if last_bid is None:
            raise InvalidBid('cannot call exact or liar as the first bid')
        freq = get_die_freq(all_die, ones_as_value=(last_bid.value if game_rules.wilds else False))
        # handle exact and liar calls
        if bid.call=='exact' and game_rules.exact:
            return freq.get(last_bid.value) == last_bid.quantity
        elif bid.call=='liar':
            return freq.get(last_bid.value) < last_bid.quantity
        else:
            raise InvalidBid('invalid call type %s'%bid.call)

def make_player_first(player_list, player):
    player_list.insert(0, player_list.pop(player_list.index(player)))
                
class Bid(object):
    def __init__(self, call='bid', quantity=0, value=0):
        self.quantity = quantity
        self.value = value
        self.call = call
        
    def __str__(self):
        if self.call!='bid':
            return self.call
        return "%s %s %ss" % (self.call, self.quantity, self.value)
        
class GameRules(object):
    def __init__(self, exact=False, wilds=False, wilds_lock=False, value_lock=False, starting_die=5, die_sides=6, bestof=False):
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
        self.bestof_target = int(math.ceil(self.games/float(self.player_count)))
        
        player_stats = {}
        for player in self.players:
            player_stats[player.name] = {None:0, True: 0, False: 0, 'derp': 0, 'wins': 0, 'losses': 0}
        
        self.log.warn('MATCH STARTS. %s GAME(S) WITH %s, RULES %s' % (self.games, ['%s'%player for player in self.players], self.rules))
        
        if self.rules.bestof:
            self.log.info('BEST OF %s: NEED %s TO WIN' % (self.games, self.bestof_target))
        
        for game in range(self.games):
            self.log.info("GAME STARTED")
        
            game_stats = {None:0, True: 0, False: 0, 'derp': 0, 'wins': 0, 'losses': 0}
            player_die = {}
            player_die_count = {}
            
            for player in self.players:
                player_die_count[player.name] = self.rules.starting_die
                player_die[player.name] = []
            
            # start the players in random order
            random.shuffle(players)
            for player in self.players:
                player.new_game(self.rules)
            
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
                    for player in players:
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
                self.log.debug('%s called %s %s and the die were: %s' % (player.name, last_player.name, bid, sorted(all_die)))
                if outcome:
                    if bid.call == 'exact':
                        self.log.debug('%s called EXACT and was SPOT ON!' % player.name)
                        make_player_first(self.players, player)
                        # all other players lose a die!
                        for all_other in active_players:
                            if all_other.name != player.name:
                                player_die_count[all_other.name] -= 1 
                    else:
                        self.log.debug('%s called LIE and was right!, %s is a liar...' % (player.name, last_player.name))
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
                for player in players:
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
                    

class Player(object):
    def __init__(self, name, *pargs, **kwargs):
        self.name = name
        self.rules = None
        self.allow_retries = True

    def get_bid(self, lastbid, *pargs, **kwargs):
        raise NotImplemented
        
    def new_round(self, players, diestate):
        raise NotImplemented    
    
    def new_game(self, players, rules):
        raise NotImplemented
        
    def inform_action(self, action):
        raise NotImplemented
        
    def __str__(self):
        return "player %s" % (self.name)

        
class Human(Player):
    def ask(self, lastbid):
        input_string = "%s it is your go. Last bid was %s, Your die are %s, enter q,v liar or exact: " % (self.name, lastbid, self.diestate)
        return raw_input(input_string)

    def new_round(self, diestate, player_die_count):
        self.diestate = diestate
        
    def get_bid(self, lastbid, *pargs, **kwargs):
        while True:
            action = self.ask(lastbid)
            if 'liar'.startswith(action):
                #os.system('cls')
                return Bid('liar')
            elif 'exact'.startswith(action):
                #os.system('cls')
                return Bid('exact')
            else:
                mybid = action.split(',', 1)
                try:
                    q = int(mybid[0])
                    v = int(mybid[1])
                except Exception, e:
                    print e
                    continue
                #os.system('cls')
                return Bid('bid', q, v)
    
    def new_game(self, rules):
        pass
        
    def inform_action(self, action):
        pass
        
class Bot(Player):
    def __init__(self, *pargs, **kwargs):
        super(Bot, self).__init__(*pargs, **kwargs)
        self.allow_retries = False
        self.settings = {}

    def new_round(self, diestate, player_die_count):
        self.diestate = diestate
        
        # first step in being a bot is to keep track of everyone's die count
        self.die_counts = player_die_count
        self.die_total = 0
        for p, c in self.die_counts.items():
            self.die_total += c
    
    def get_bid(self, lastbid, *pargs, **kwargs):
        # this default bot behaves quite randomly, no understanding of its own die
        # it is interesting to play, but it has little hope of winning, useful for fuzz-testing the GM
        if lastbid is None:
            q = random.randint(1,self.die_total)
            v = random.randint(1,self.rules.die_sides)
        else:
            # randomly pick an action
            r = random.random()
            if (r < self.settings.get('liar_chance', 0)) or lastbid.quantity > self.die_total or lastbid.value > self.rules.die_sides:
                return Bid('liar')
            elif self.rules.exact and r < 0.1:
                return Bid('exact')
            else:
                # increment either the value or the quantity
                p = random.random()
                q = lastbid.quantity
                v = lastbid.value
                if v >= self.rules.die_sides or kwargs.get('value_lock'):
                    z = 0 
                else:
                    z = 0.5
                if (p > z):
                    q += 1
                else:
                    v = random.randint(v+1, self.rules.die_sides)
        return Bid('bid', q, v)
    
    def new_game(self, rules):
        self.rules = rules
        
    def inform_action(self, action):
        pass
        
class MinMaxBot(Bot):
    def get_bid(self, lastbid, *pargs, **kwargs):
        # this bot tries to play as safe as possible and doesn't make 'liar' calls unless it has to. no understanding of its own die
        if lastbid is None:
            # always start with the smallest estimate to maximise safety!
            q = 1
            # always start with sixes to annoy people
            v = self.rules.die_sides
        else:
            r = random.random()
            if (r < self.settings.get('liar_chance', 0)) or lastbid.quantity > self.die_total or lastbid.value > self.rules.die_sides:
                return Bid('liar')
            else:
                q = lastbid.quantity + 1
                v = lastbid.value
        return Bid('bid', q, v)

class MathsBot(Bot):
    def new_round(self, diestate, player_die_count):
        super(MathsBot, self).new_round(diestate, player_die_count)
        self.my_die_freqs = get_die_freq(self.diestate)
        max_f = 0
        max_v = 0
        ones = 0
        for v, f in self.my_die_freqs.items():
            if v==1:
                ones = f
            elif f > max_f or f==max_f and v>max_v:
                max_f = f
                max_v = v
        self.max_freq = max_f
        self.max_value = max_v
        
        # number of die of one value that the others should contribute on average
        self.expect_in_others = int((self.die_total - len(self.diestate)) / float(self.rules.die_sides))
        self.safe_estimate = self.max_freq + self.expect_in_others
        if self.rules.wilds:
            self.safe_estimate = self.safe_estimate + ones + self.expect_in_others
        #print self.safe_estimate

    def get_bid(self, lastbid, *pargs, **kwargs):
        # this bot understands its own hand and uses this to influence starting bids and 'liar' calls 
    
        if lastbid is None:
            # always start with the largest safe estimate (although this may give our game away)
            q = self.safe_estimate
            v = self.max_value
        else:
            # now we gotta be clever. and typing these words doesn't seem to help.
            if lastbid.quantity > self.die_total or lastbid.value > self.rules.die_sides or lastbid.quantity > self.safe_estimate:
                return Bid('liar')
            # the exact rule is too much of a gamble, at least with this level of intelligence
            # elif self.rules.exact and lastbid.quantity == self.safe_estimate:
                # return Bid('exact')
            else:
                q = lastbid.quantity + 1
                v = lastbid.value
        return Bid('bid', q, v)
        
class BayesBot(MathsBot):
    def get_bid(self, lastbid, *pargs, **kwargs):
        # this bot understands its own hand and uses this to influence starting bids, 'liar' calls and bids
        
        # iterate every possible call
        calls = []
        for i in range(lastbid.value, self.rules.die_sides+1):
            # for every value, find a good quantity to bid, given what we know (e.g. if we have 5 sixes, it may be worth betting 7 sixes):
            # P(A|B) = P(B|A)*P(A) / P(B)
            # WHERE A='at least 3 5s in total' and B='my cup has two 5s'
            # P(B|A) or 'what is the chance I have two 5s when there are at least 3 5s in total'
            
            # P(A) is get_unbiased_probability_gte(total, 3)
            # P(B) is get_unbiased_probability_exact(mycup, 2)
            # although these numbers can be doubled if wilds are in play
            pass
    
        if lastbid is None:
            # always start with the largest safe estimate (although this may give our game away)
            q = max(self.max_freq, int(self.expected_qty))
            v = self.max_value
        else:
            if lastbid.quantity > self.die_total or lastbid.value > self.rules.die_sides or lastbid.quantity > max(self.expected_qty, self.max_freq):
                return Bid('liar')
            else:
                q = lastbid.quantity + 1
                v = lastbid.value
        return Bid('bid', q, v)

def nCk(n,k): 
  return int( reduce(mul, (Fraction(n-i, i+1) for i in range(k)), 1) )
        
def get_unbiased_probability_exact(total_die, die_sides, quantity):
    """
    the probability that in total_die, there are exactly quantity die (of any given face)
    """
    die_sides = float(die_sides)
    return nCk(total_die, quantity) * ((1/die_sides)**quantity) * (((die_sides-1)/die_sides)**(total_die-quantity))
        
def get_unbiased_probability_gte(total_die, die_sides, quantity):
    """
    the probability that in total_die, there are at least quantity die (of any given face)
    """
    probability = 0
    for q in range(quantity, total_die+1):
        probability += get_unbiased_probability_exact(total_die, die_sides, q)
    return probability
        
def get_probability_mine_given_total(total_die, die_sides, my_quantity, my_total):
    """
    # P(B|A) or 'what is the chance I have two 5s when there are at least 3 5s in total'
    """
    pass
        
if __name__ == '__main__':
    """
    not all the bots understand all the rules
    of course, playing as a human it shouldn't be too difficult to figure the bids out from the error messages
    """
    p1 = Human('bob')
    p2 = Human('sally')
    p3 = MinMaxBot('minnie')
    p4 = MathsBot('computron')
    p5 = Bot('randy')
    p6 = BayesBot('babo') 
    
    #players = [p1,p2] # two humans
    #players = [p1,p4] # human vs mathsbot
    #players = [p3,p5] # two dumb bots
    #players = [p3,p4,p5] # all the bots
    players = [Bot(str(i)) for i in range(9)] + [MathsBot('one_vs_all')] # skynet
    
    rules = GameRules(starting_die=6, exact=True, wilds=True, wilds_lock=False, value_lock=True, bestof=True)
    match = Match(rules, games=1000, loglevel=logging.WARN)
    for player in players:
        match.addPlayer(player)
    match.run()
