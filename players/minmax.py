from .bot import Bot
import random


class MinMaxBot(Bot):
    def get_bid(self, lastbid, *pargs, **kwargs):
        # this bot tries to play as safe as possible
        # and doesn't make 'liar' calls unless it has to. no understanding of its own die
        if lastbid is None:
            # always start with the smallest estimate to maximise safety!
            q = 1
            # always start with sixes to annoy people
            v = self.rules.die_sides
        else:
            r = random.random()
            if (r < self.settings.get('liar_chance', 0)) or self.idiocy_check(lastbid):
                return self.Bid('liar')
            else:
                q = lastbid.quantity + 1
                v = lastbid.value
        return self.Bid('bid', q, v)
