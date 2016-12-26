def get_die_freq(all_die, ones_as_value=False):
    """
    returns a frequency map of {value: quantity} for the die
    ones_as_values - any ones get replaced with this value during counting
    frequency map has no entries for die with frequency 0
    """
    freq = {}
    for die in all_die:
        if (ones_as_value and die == 1):
            die = ones_as_value
        freq.setdefault(die, 0)
        freq[die] += 1

    return freq


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


class Bid(object):
    def __init__(self, call='bid', quantity=0, value=0):
        self.quantity = quantity
        self.value = value
        self.call = call

    def __str__(self):
        if self.call != 'bid':
            return self.call
        return "%s %s %ss" % (self.call, self.quantity, self.value)
