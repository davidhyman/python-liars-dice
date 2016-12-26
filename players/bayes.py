from .mathsbot import MathsBot
from operator import mul
from fractions import Fraction


class BayesBot(MathsBot):
    def get_bid(self, lastbid, *pargs, **kwargs):
        # this bot understands its own hand and uses this to influence starting bids, 'liar' calls and bids

        # iterate every possible call
        calls = []
        for i in range(lastbid.value, self.rules.die_sides + 1):
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
            if lastbid.quantity > self.die_total or lastbid.value > self.rules.die_sides or lastbid.quantity > max(
                    self.expected_qty, self.max_freq):
                return self.Bid('liar')
            else:
                q = lastbid.quantity + 1
                v = lastbid.value
        return self.Bid('bid', q, v)


def nCk(n, k):
    return int(reduce(mul, (Fraction(n - i, i + 1) for i in range(k)), 1))


def get_unbiased_probability_exact(total_die, die_sides, quantity):
    """
    the probability that in total_die, there are exactly quantity die (of any given face)
    """
    die_sides = float(die_sides)
    return nCk(total_die, quantity) * ((1 / die_sides) ** quantity) * (
    ((die_sides - 1) / die_sides) ** (total_die - quantity))


def get_unbiased_probability_gte(total_die, die_sides, quantity):
    """
    the probability that in total_die, there are at least quantity die (of any given face)
    """
    probability = 0
    for q in range(quantity, total_die + 1):
        probability += get_unbiased_probability_exact(total_die, die_sides, q)
    return probability


def get_probability_mine_given_total(total_die, die_sides, my_quantity, my_total):
    """
    # P(B|A) or 'what is the chance I have two 5s when there are at least 3 5s in total'
    """
    pass
