import base64
import datetime
import json
import logging
import os
import redis
import requests
import socket
import time

from urllib3 import exceptions
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


class NBATeamError(Exception):
    """Base class for NBATeam Errors"""
    pass


class NHLException(Exception):
    """Base class for NHLTeam Errors"""
    pass


class NHLTeamError(Exception):
    """Base class for NHLTeam Errors"""
    pass


class NHLPlayerError(Exception):
    """Base class for NHLTeam Errors"""
    pass


class NHLPlayerException(Exception):
    """Base class for NHLTeam Errors"""
    pass


class NHLRequestException(NHLException):
    """Base class for NHL request exceptions"""
    pass


class NBATeam(object):
    """
    Create an NBA Team object
    """
    def __init__(self, api_key, team):
        self.api_key = api_key
        self.nba_teams = self.get_nba_teams()
        self.team = self.get_team_abbreviation(team)
        self.schedule_data = self.request_schedule()
        self.schedule = self.get_schedule()
        self.completed_games = self.get_completed_games()
        self.unplayed_games = self.get_unplayed_games()
        self.standings = self.request_standings()
        self.team_stats = self.get_team_stats()
        self.team_leaders = self.get_team_leaders()

    def get_nba_teams(self):
        """
        Get NBA team config
        """
        with open('config/nba.json', 'r') as f:
            teams = json.load(f)

        return teams

    def get_team_abbreviation(self, team):
        """
        Get the team's abbreviation so their data can be extracted from API
        """
        abbreviation = self.nba_teams['abbreviations'].get(team.lower())
        if not abbreviation:
            raise NBATeamError(f'Unrecognized team: {team}')

        return abbreviation

    def request_schedule(self):
        """
        Retrieve league season schedule from MYSPORTSFEEDS API
        """
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime('%Y%m%d')
        url = 'https://api.mysportsfeeds.com/v2.0/pull/nba/2018-2019-regular/games.json'
        encoded_key = base64.b64encode('{}:MYSPORTSFEEDS'.format(self.api_key).encode('utf-8')).decode('ascii')
        headers = {
            "Authorization": "Basic " + encoded_key
        }
        params = {'fordate': formatted_time}
        try:
            request = requests.get(url, headers=headers, params=params, verify=False)
            print(request.status_code)
        except ConnectionError as err:
            raise NBATeamError('API Connection Error')
        if request.status_code != 200:
            raise NBATeamError(f'Error with API request: {request.status_code}')
        data = request.json()

        return data

    def get_schedule(self):
        """
        Parse games for team schedule from full league schedule
        Return full schedule with results of completed games
        """
        schedule = self.schedule_data
        games = len(schedule['games'])
        team_schedule = []
        for i in range(games):
            game = schedule['games'][i]['schedule']
            home_team = game['homeTeam']['abbreviation']
            away_team = game['awayTeam']['abbreviation']
            if home_team == self.team or away_team == self.team:
                add_game = {}
                add_game['id'] = game['id']
                add_game['date'] = game['startTime']
                add_game['home_team'] = game['homeTeam']['abbreviation']
                add_game['away_team'] = game['awayTeam']['abbreviation']
                if game['playedStatus'] == 'COMPLETED':
                    add_game['score'] = schedule['games'][i]['score']
                team_schedule.append(add_game)

        return team_schedule

    def get_completed_games(self):
        """
        Get list of completed games from schedule
        """
        games = self.schedule
        completed_games = []
        for i in range(len(games)):
            game = games[i].get('score')
            if game:
                completed_games.append(games[i])

        return completed_games

    def get_previous_games(self, games=None):
        """
        Get a teams previous played games. If games isn't specified
        get all completed games
        """
        if not games:
            previous_games = self.completed_games
        else:
            games_played = len(self.completed_games)
            num_games = games_played - int(games)
            previous_games = self.completed_games[num_games:]

        return previous_games

    def get_unplayed_games(self):
        """
        Get list of unplayed games from schedule
        """
        games = self.schedule
        unplayed_games = []
        for i in range(len(games)):
            game = games[i].get('score')
            if not game:
                unplayed_games.append(games[i])

        return unplayed_games

    def get_upcoming_games(self, games=None):
        """
        Get a teams upcoming games. If games isn't specified
        get all games
        """
        if not games:
            upcoming_games = self.unplayed_games[0]
        else:
            upcoming_games = self.unplayed_games[:int(games)]

        return upcoming_games

    def request_standings(self):
        """
        Retrieve the team's standings
        Return teams current position in league, division, and conference
        """
        url = 'https://api.mysportsfeeds.com/v2.0/pull/nba/2018-2019-regular/standings.json'
        current_time = datetime.datetime.now()
        formatted_time = current_time.strftime('%Y%m%d')
        encoded_key = base64.b64encode('{}:MYSPORTSFEEDS'.format(self.api_key).encode('utf-8')).decode('ascii')
        headers = {
            "Authorization": "Basic " + encoded_key
        }
        params = {'fordate': formatted_time, 'team': self.team}
        try:
            request = requests.get(url, headers=headers, params=params, verify=False)
            print(request.status_code)
        except ConnectionError as err:
            raise NBATeamError('API Connection Error')
        if request.status_code != 200:
            raise NBATeamError(f'Error with API request: {request.status_code}')
        data = request.json()
        #print(json.dumps(data, indent=4))
        return data

    def get_team_stats(self):
        """
        Retrieve team's stats
        Return position for stats like rebounding, points for, etc.
        """
        return

    def get_team_leaders(self):
        """
        Retrieve the team's leader in stats
        Return team leader for stats such as avg. points, rebounding etc.
        """
        return


class NHLTeam:
    """
    Create NHL team object
    """
    def __init__(self, api_key, team=None):
        self.session = requests.session()
        self._api_key = api_key
        self._config = self._get_config()
        self.base_url = 'https://statsapi.web.nhl.com/api/v1/'
        self._nhl_teams = self._config['teams']
        self._emojis = self._config['emojis']
        self.players = redis.StrictRedis(host='jal_redis.backend', port=6379, db=0)
        if team:
            self.team = self._get_team_id(team)
            self.team_info = self.get_team_info(self.team)
            self.team_name = self.team_info['name']
            self.team_venue = self.team_info['venue']['name']
            self.team_stats = self.get_team_stats()
            self.roster = self.get_team_roster()
            self.schedule = self.get_full_schedule()
            self.game_results, self.unplayed_games = self.parse_schedule(self.schedule)

    def _fetch_all_teams(self):
        """
        Get the API metadata id for all NHL teams
        """
        url = f'{self.base_url}teams'
        data = self._nhl_request(url)
        return data

    def _get_config(self):
        """
        Get NHL team config
        """
        with open('config/nhl_config.json', 'r') as f:
            teams = json.load(f)

        return teams

    def _get_team_id(self, team):
        """
        Get the API id for a provided team
        """
        teams = self._nhl_teams
        if team.lower() not in teams.keys():
            raise NHLTeamError(f"Unrecognized team: {team}")
        team_id = teams.get(team.lower())
        if not team_id:
            raise NHLTeam(f"Unrecognized team: {team}")
        return team_id

    def _nhl_request(self, url):
        """
        GET request to NHL API
        """
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        try:
            request = self.session.get(url)
        except socket.gaierror:
            time.sleep(1)
            request = self.session.get(url)
        except requests.exceptions.ConnectionError:
            time.sleep(2)
            request = self.session.get(url)

        if request.status_code != 200:
            logging.error(f"Error with NHL API request | status: {request.status_code}\n{request.content}")
            data = None
        else:
            data = request.json()
        return data

    def get_team_info(self, team):
        """
        Get general team information
        """
        if not team:
            return
        url = f"{self.base_url}teams/{team}"
        data = self._nhl_request(url)
        if data:
            team_info = data['teams'][0]
            return team_info

    def get_player_info(self, player):
        """
        Get individual stats for a player
        """
        player = self.players.get(player)
        if not player:
            raise NHLPlayerError('Player Not Found')
        url = f"{self.base_url}people/{player.decode()}"
        data = self._nhl_request(url)
        if data:
            info = data['people'][0]
            return info

    def get_player_season_stats(self, player, season=None):
        """
        Get individual stats for a player
        """
        player_id = self.players.get(player)
        player_info = self.get_player_info(player)
        team = player_info['currentTeam']['id']
        if not player_id:
            raise NHLPlayerError('Player Not Found')
        if not season:
            season = '20182019'
        endpoint = f"/stats?stats=statsSingleSeason&season={season}"
        url = f"{self.base_url}people/{player_id.decode()}{endpoint}"
        data = self._nhl_request(url)
        if data:
            stats = data['stats'][0]['splits'][0]
            stats['team'] = team
            return stats

    def get_career_stats(self, player):
        """
        Get career stats for a player
        """
        player_id = self.players.get(player)
        # player_info = self.get_player_info(player)
        if not player_id:
            raise NHLPlayerError('Player Not Found')
        endpoint = "stats?stats=yearByYear"
        url = f"{self.base_url}people/{player_id.decode()}/{endpoint}"
        data = self._nhl_request(url)
        if data:
            seasons = data['stats'][0]['splits']
            return seasons

    def get_team_stats(self, team=None):
        """
        Get team stats. Return team stats object
        """
        if not team:
            team = self.team
        url = f"{self.base_url}teams/{team}?expand=team.stats"
        data = self._nhl_request(url)
        return data['teams'][0]

    def get_team_roster(self, team=None):
        """
        Get team roster. Return list of player objects
        """
        if not team:
            team = self.team
        url = f"{self.base_url}teams/{team}/roster"
        data = self._nhl_request(url)
        player_list = data['roster']
        return player_list

    @property
    def todays_games(self):
        """
        Get NHL games being played today
        """
        games = {}
        url = f"{self.base_url}schedule"
        data = self._nhl_request(url)
        if data:
            games['date'] = data['dates'][0]['date']
            games_list = data['dates'][0]['games']
            games['games'] = games_list
            return games

    def get_full_schedule(self, team=None, season='20182019'):
        """
        Get team schedule. Return list of game objects
        """
        if not team:
            team = self.team
        url = f"{self.base_url}schedule?teamId={team}&season={season}"
        data = self._nhl_request(url)
        game_list = data['dates']
        return game_list

    def parse_schedule(self, schedule):
        """
        Get results of completed games
        """
        completed_games = []
        unplayed_games = []
        for i in range(len(schedule)):
            game = {'away_team': {}, 'home_team': {}}
            game_info = schedule[i]['games'][0]
            status = game_info['status']['abstractGameState']
            teams = game_info['teams']
            if game_info['gameType'] != 'PR' and status == 'Final':
                game['date'] = game_info['gameDate']
                game['away_team']['name'] = teams['away']['team']['name']
                game['away_team']['score'] = teams['away']['score']
                game['home_team']['name'] = teams['home']['team']['name']
                game['home_team']['score'] = teams['home']['score']
                completed_games.append(game)
            elif game_info['gameType'] != 'PR' and status == 'Preview':
                game['date'] = game_info['gameDate']
                game['away_team']['name'] = teams['away']['team']['name']
                game['home_team']['name'] = teams['home']['team']['name']
                unplayed_games.append(game)
        return completed_games, unplayed_games

    def _fetch_standings(self):
        """
        Get current NHL standings
        """
        url = f'{self.base_url}standings'
        request = requests.get(url)
        if request.status != 200:
            raise NHLTeamError('Error with API request')
        data = request.json()
        return data


class NFLTeam(object):
    """
    Create NFL team object
    """
    def __init__(self, team):
        pass


class MLBTeam(object):
    """
    Create MLB team object
    """
    def __init__(self, team):
        pass


def main():
    """
    Main function
    """
    print('NBA Team Information')
    api_key = os.environ.get('MYSPORTSFEEDS_API_KEY')
    celtics = NBATeam(api_key, 'boston')
    standings = celtics.request_standings()
    # print(json.dumps(standings['teams'][0]['stats'], indent=4))
    print(standings['teams'])
    #games = celtics.completed_games
    #for game in games:
    #    print(json.dumps(game, indent=4))


if __name__ == '__main__':
    main()
