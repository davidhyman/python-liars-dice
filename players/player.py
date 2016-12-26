import abc
from helpers import Bid


class Player(object):
    __metaclass__ = abc.ABCMeta

    Bid = Bid
    name = None
    rules = None
    allow_retries = False

    def __init__(self, name, **settings):
        self.name = name
        self.settings = settings if settings else {}

    @abc.abstractmethod
    def get_bid(self, lastbid):
        """
        what is your bid?
        :param lastbid:
        :return:
        """
        pass

    @abc.abstractmethod
    def new_round(self, players, diestate):
        """
        actions on starting a new round
        :param players:
        :param diestate:
        :return:
        """
        pass

    @abc.abstractmethod
    def new_game(self, players, rules):
        """
        actions on starting a new game
        :param players:
        :param rules:
        :return:
        """
        pass

    def __str__(self):
        return "%s player %s" % (self.__class__.__name__, self.name)
