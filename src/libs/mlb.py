import datetime
import json
import logging
import requests

from datetime import timedelta
from pytz import timezone
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from utils.BotTools import get_config
from utils.exceptions import MLBException

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


BASE_URL = 'https://statsapi.mlb.com/api/v1/'

CONFIG = get_config('mlb.json')


class MLB:
    def __init__(self):
        self.current_season = datetime.datetime.strftime(self.date, "%Y")
        pass

class MLBStandings(MLB):
    def __init__(self):
        super().__init__()
        self.overall = self._get_overall_standings()
        self.american_league = self._get_league_standings('american')
        self.national_league = self._get_league_standings('national')
        self.al_east = self._get_division_standings('american', 'east')
        self.al_central = self._get_division_standings('american', 'central')
        self.al_west = self._get_division_standings('american', 'west')
        self.nl_east = self._get_division_standings('national', 'east')
        self.nl_central = self._get_division_standings('national', 'central')
        self.nl_west = self._get_division_standings('national', 'west')
        pass

    def _get_overall_standings(self):
        pass

    def _get_league_standings(self, league):
        pass

    def _get_division_standings(self, league, division):
        pass


class MLBTeam(MLB):
    def __init__(self):
        super().__init__()
        self.team_hitting_stats = self._get_team_hitting_stats()
        self.team_pitching_stats = self.get_team_pitching_stats()
        self.record = self._get_team_record()
        self.schedule = self._get_team_schedule()


class MLBPlayer(MLB):
    def __init__(self, player):
        super().__init__()
        self.player = player
        self.current_season_stats = self._get_player_season_stats(self.current_season)
        pass

        def _get_player_season_stats(self, season):
            """
            Get players stats for a given season
            """
            pass
