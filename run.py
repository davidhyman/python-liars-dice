import players
from liar import Match, GameRules
import logging


if __name__ == '__main__':
    """
    not all the bots understand all the rules
    of course, playing as a human it shouldn't be too difficult to figure the bids out from the error messages
    """
    name = raw_input('hello, what is your name?:')
    p1 = players.Human(name)
    #p2 = players.Human('sally')
    #p3 = MinMaxBot('minnie')
    p4 = players.MathsBot('computron')
    #p5 = Bot('randy')
    #p6 = BayesBot('babo')

    # players = [p1,p2] # two humans
    players = [p1,p4] # human vs mathsbot
    # players = [p3,p5] # two dumb bots
    # players = [p3,p4,p5] # all the bots
    #players = [players.RandomBot(str(i)) for i in range(9)] + [players.MathsBot('one_vs_all')]

    rules = GameRules(starting_die=5, exact=False, wilds=False, wilds_lock=False, value_lock=False, bestof=False)
    match = Match(rules, games=1, loglevel=logging.DEBUG)
    for player in players:
        match.addPlayer(player)
    match.run()
