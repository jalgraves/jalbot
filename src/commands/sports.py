
import datetime
import json
import os
import logging  # noqa

from libs.Sports import NBATeam
from libs.Sports import MLBTeam
from libs.slack_nhl import SlackNHL
from libs.slack_nfl import SlackNFL
from libs.slack_nba import SlackNBA
from libs.slack_mlb import SlackMLB
from utils.exceptions import JalBotError
from utils.BotTools import get_config, try_request
from utils.slackparse import SlackArgParse


class BotCommand(object):
    """Create Geo object from Slack event"""
    def __init__(self, event, user):
        self.text = event['text']
        self.api_key = os.environ.get('MYSPORTSFEEDS_API_KEY')
        self.config = get_config('sports.json')
        self.parsed_args = SlackArgParse(self.config['valid_args'], self.config['options'], event['text'])
        self.args = self.parsed_args.args
        self.option = self.parsed_args.option
        self.league = self._get_league()
        self.player = self._get_player()
        self.team_name = self._get_team_name()
        self.matchup = self._get_matchup()
        self.response = self.run_cmd()

    def run_cmd(self):
        if self.text.split()[1] == 'help':
            response = "\n".join(self.config['help'])
        else:
            league_command = {
                'nba': SlackNBA,
                'nfl': SlackNFL,
                'nhl': SlackNHL,
                'mlb': SlackMLB
            }
            command = league_command.get(self.league)
            response = command(self.args, self.option, self.team_name, self.player)
        return response.reply

    def example_request(self):
        """example request using try_request wrapper"""
        url = self.config['url']
        request = try_request('example', 'POST', url, data="", verify=False, timeout=10)
        return request

    def _get_league(self):
        """
        Get the league for the requested command
        """
        league = self.args.get('league')
        if not league:
            raise JalBotError('Missing required argument -l|-league')
        return league.lower()

    def _get_team_name(self):
        """
        Get team name from Slack args
        """
        return self.args.get('team')

    def _get_matchup(self):
        """
        Get team matchup
        """
        return self.args.get('matchup')

    def _get_player(self):
        """
        Get player from args
        """
        player = self.args.get('player')
        if player:
            player = player.title()
        return player

    def _format_date(self, date):
        """
        Format date from API into Month Day
        """
        if 'T' in date:
            date, game_time = date.split('T')
        game_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        day = game_date.strftime("%d")
        if day.startswith('0'):
            day = day[1:]
        formatted_date = game_date.strftime(f"%A, %B {day}")

        return formatted_date

    def _format_number(self, num):
        """
        Get suffix to append to number
        """
        num = int(num)
        if num in [1, 21, 31]:
            suffix = 'st'
        elif num in [2, 22, 32]:
            suffix = 'nd'
        elif num in [3, 23, 33]:
            suffix = 'rd'
        else:
            suffix = 'th'

        return f"{num}{suffix}"
