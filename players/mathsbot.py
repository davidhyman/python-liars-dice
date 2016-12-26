from .bot import Bot
from helpers import get_die_freq


class MathsBot(Bot):
    def new_round(self, diestate, player_die_count):
        super(MathsBot, self).new_round(diestate, player_die_count)
        self.my_die_freqs = get_die_freq(self.diestate)
        max_f = 0
        max_v = 0
        ones = 0
        for v, f in self.my_die_freqs.items():
            if v == 1:
                ones = f
            elif f > max_f or f == max_f and v > max_v:
                max_f = f
                max_v = v
        self.max_freq = max_f
        self.max_value = max_v

        # number of die of one value that the others should contribute on average
        self.expect_in_others = int((self.die_total - len(self.diestate)) / float(self.rules.die_sides))
        self.safe_estimate = self.max_freq + self.expect_in_others
        if self.rules.wilds:
            self.safe_estimate = self.safe_estimate + ones + self.expect_in_others
            # print self.safe_estimate

    def get_bid(self, lastbid, *pargs, **kwargs):
        # this bot understands its own hand and uses this to influence starting bids and 'liar' calls

        if lastbid is None:
            # always start with the largest safe estimate (although this may give our game away)
            q = self.safe_estimate
            v = self.max_value
        else:
            # now we gotta be clever. and typing these words doesn't seem to help.
            if lastbid.quantity > self.die_total or lastbid.value > self.rules.die_sides or lastbid.quantity > self.safe_estimate:
                return self.Bid('liar')
                # the exact rule is too much of a gamble, at least with this level of intelligence
                # elif self.rules.exact and lastbid.quantity == self.safe_estimate:
                # return Bid('exact')
            else:
                q = lastbid.quantity + 1
                v = lastbid.value
        return self.Bid('bid', q, v)
