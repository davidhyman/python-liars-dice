from .player import Player
from helpers import get_die_freq
import os


class Human(Player):
    allow_retries = True

    def ask(self, lastbid):
        equiv = get_die_freq(self.diestate, ones_as_value=(lastbid.value if self.rules.wilds else False))
        equiv_str = " ".join('%sx%s' % (k, v) for k, v in sorted(equiv.items()))
        input_string = "%s it is your go. Last bid was %s, Your die are %s,  \nThe equivalent counts are %s\nenter q,v liar%s: " % (
            self.name, lastbid, self.diestate, equiv_str, " or exact" if self.rules.exact else ""
        )
        get = raw_input(input_string)
        os.system('cls')
        return get

    def new_game(self, players, rules):
        print "oh look, it's a new game"
        self.rules = rules

    def new_round(self, diestate, player_die_count):
        self.diestate = diestate

    def get_bid(self, lastbid, *pargs, **kwargs):
        while True:  # human is allowed to retry if they pass an invalid bid...
            action = self.ask(lastbid)
            if 'liar'.startswith(action):
                return self.Bid('liar')
            elif 'exact'.startswith(action):
                return self.Bid('exact')
            else:
                mybid = action.split(',', 1)
                try:
                    q = int(mybid[0])
                    v = int(mybid[1])
                except Exception, e:
                    print e
                    continue
                return self.Bid('bid', q, v)
