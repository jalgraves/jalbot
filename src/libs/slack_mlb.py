import datetime
import logging
import json

# from libs.mlb import MLBTeam
from libs.mlb import MLB, MLBStandings
from utils.BotTools import get_config
from utils.exceptions import MLBException


class SlackMLB:
    """
    Create a Slack response object`
    """
    def __init__(self, args, option, team=None, player=None):
        self.args = args
        self.option = option
        self.team = team
        self.player = player
        self.config = get_config('mlb.json')

    @property
    def reply(self):
        """
        Return Slack formatted message reply
        """
        options = {
            'scores': self.mlb_scores_reply,
            'schedule': self.mlb_schedule_reply,
            # 'stats': self.mlb_stats_reply,
            # 'roster': self.mlb_roster,
            # 'career': self.mlb_career_stats,
            'standings': self.mlb_standings_reply
        }
        option = options.get(self.option)
        response = option()
        return response

    def mlb_scores_reply(self):
        """
        Build Slack reply containing MLB game score info
        """
        pass

    def mlb_schedule_reply(self):
        """
        Build Slack reply containing MLB game schedule info
        """
        return ":mlb_bos: *Boston Red Sox*"

    def mlb_standings_reply(self):
        """
        Build Slack reply containing MLB standings info
        """
        pass
