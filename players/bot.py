from .player import Player


class Bot(Player):
    def idiocy_check(self, lastbid):
        """
        if your opponent called an impossible qv pair, call them
        :param lastbid:
        :return: True if impossible
        """
        return lastbid.quantity > self.die_total or lastbid.value > self.rules.die_sides

    def new_round(self, diestate, player_die_count):
        self.diestate = diestate

        # first step in being a bot is to keep track of everyone's die count
        self.die_counts = player_die_count
        self.die_total = 0
        for p, c in self.die_counts.items():
            self.die_total += c

    def new_game(self, players, rules):
        self.other_players = players
        self.rules = rules
