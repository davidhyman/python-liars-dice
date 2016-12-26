from .bot import Bot
import random


class RandomBot(Bot):
    def __init__(self, *pargs, **kwargs):
        super(Bot, self).__init__(*pargs, **kwargs)
        self.allow_retries = False
        self.settings = {}

    def get_bid(self, lastbid, *pargs, **kwargs):
        # this default bot behaves quite randomly, no understanding of its own die
        # it is interesting to play, but it has little hope of winning, useful for fuzz-testing the GM
        if lastbid is None:
            q = random.randint(1, self.die_total)
            v = random.randint(1, self.rules.die_sides)
        else:
            # randomly pick an action
            r = random.random()
            if (r < self.settings.get('liar_chance', 0)) or self.idiocy_check(lastbid):
                return self.Bid('liar')
            elif self.rules.exact and r < 0.1:
                return self.Bid('exact')
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
                    v = random.randint(v + 1, self.rules.die_sides)
        return self.Bid('bid', q, v)
