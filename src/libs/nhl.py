import datetime
import json
import logging
import redis
import requests
import socket
import sys
import time

from datetime import timedelta
from pytz import timezone
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from utils.exceptions import NHLException
from utils.exceptions import NHLTeamException
from utils.exceptions import NHLPlayerException
from utils.exceptions import NHLRequestException


class NHL:
    """
    Create NHL object
    """
    def __init__(self):
        self._date = datetime.datetime.now(timezone('US/Eastern'))
        self._session = requests.session()
        self._config = self._get_config()
        self._base_url = 'https://statsapi.web.nhl.com/api/v1/'
        self._team_list = self._config['teams']

    @property
    def todays_games(self):
        """
        Get NHL games being played today
        """
        date = datetime.datetime.strftime(self._date, "%Y-%m-%d")
        games = {}
        url = f"{self._base_url}schedule?date={date}"
        data = self._nhl_request(url)
        if data:
            if data['totalGames'] == 0:
                return None
            games['date'] = data['dates'][0]['date']
            games_list = data['dates'][0]['games']
            games['games'] = games_list
            return games

    @property
    def recent_games(self):
        """
        Get games played yesterday
        """
        date = (self._date - timedelta(1)).strftime('%Y-%m-%d')
        games = {}
        url = f"{self._base_url}schedule?date={date}"
        data = self._nhl_request(url)
        if data:
            if data['totalGames'] == 0:
                return None
            games['date'] = data['dates'][0]['date']
            games_list = data['dates'][0]['games']
            games['games'] = games_list
            return games

    @property
    def standings(self):
        """
        Get current NHL standings
        """
        divisions = self.get_standings()
        standings = {
            'conference': {
                'Eastern': {},
                'Western': {}
            },
            'division': {
                'Metropolitan': {},
                'Atlantic': {},
                'Central': {},
                'Pacific': {}
            },
            'league': {},
            'records': {}
        }
        for div in divisions:
            division_name = div['division']['name']
            conference_name = div['conference']['name']
            teams = div['teamRecords']
            for team in teams:
                name = team['team']['name']
                division_rank = team['divisionRank']
                conference_rank = team['conferenceRank']
                league_rank = team['leagueRank']
                record = team['leagueRecord']
                points = team['points']
                games_played = team['gamesPlayed']
                standings['conference'][conference_name][name] = conference_rank
                standings['division'][division_name][name] = division_rank
                standings['league'][name] = league_rank
                standings['records'][name] = self.stringify_record(record, points, games_played)
        return standings

    def stringify_record(self, record, points, games):
        """
        Convert team record dict into string
        """
        wins = record['wins']
        losses = record['losses']
        ot = record['ot']
        record = f"{wins}-{losses}-{ot}-{points} (GP {games})"
        return record

    def get_standings(self):
        """
        Return a list containing four dicts with stats and team info for each
        separate division in the NHL
        """
        url = f'{self._base_url}standings'
        data = self._nhl_request(url)
        if data:
            division_list = data['records']
            return division_list

    def _nhl_request(self, url):
        """
        GET request to NHL API
        """
        retries = Retry(total=5, backoff_factor=1, status_forcelist=[502, 503, 504])
        self._session.mount('http://', HTTPAdapter(max_retries=retries))
        try:
            request = self._session.get(url, verify=False)
        except socket.gaierror:
            time.sleep(1)
            request = self._session.get(url)
        except requests.exceptions.ConnectionError:
            time.sleep(2)
            request = self._session.get(url)
        if request.status_code != 200:
            error_message = f"Error with NHL API request | status: {request.status_code}\n{request.content}"
            logging.error(error_message)
            raise NHLRequestException(error_message)
        else:
            data = request.json()
        return data

    def _parse_schedule(self, schedule):
        """
        Get results of completed games
        """
        completed_games = []
        unplayed_games = []
        for game in schedule:
            game_data = {'away_team': {}, 'home_team': {}}
            game_info = game['games'][0]
            status = game_info['status']['abstractGameState']
            teams = game_info['teams']
            if game_info['gameType'] != 'PR' and status == 'Final':
                game_data['date'] = game['date']
                game_data['away_team']['name'] = teams['away']['team']['name']
                game_data['away_team']['score'] = teams['away']['score']
                game_data['home_team']['name'] = teams['home']['team']['name']
                game_data['home_team']['score'] = teams['home']['score']
                completed_games.append(game_data)
            elif game_info['gameType'] != 'PR' and status == 'Preview':
                game_data['date'] = game['date']
                game_data['away_team']['name'] = teams['away']['team']['name']
                game_data['home_team']['name'] = teams['home']['team']['name']
                unplayed_games.append(game_data)
        return completed_games, unplayed_games

    def _get_config(self):
        """
        Get NHL config
        """
        with open('/jalbot/config/nhl_config.json', 'r') as f:
            config = json.load(f)
        return config


class NHLLeague(NHL):
    """
    Create NHL league object
    """
    def __init__(self):
        super().__init__()
        self.live_scores = self.get_game_scores(status='Live', games=self.todays_games)
        self.recent_scores = self.get_game_scores(status='Final', games=self.recent_games)

    def get_game_scores(self, status, games=None):
        game_scores = []
        if not games:
            return
        parse_games = games['games']
        for game in parse_games:
            game_data = {'away_team': {}, 'home_team': {}}
            game_status = game['status']['abstractGameState']
            teams = game['teams']
            if game['gameType'] != 'PR' and game_status == status:
                game_data['date'] = games['date']
                game_data['away_team']['name'] = teams['away']['team']['name']
                game_data['away_team']['score'] = teams['away']['score']
                game_data['home_team']['name'] = teams['home']['team']['name']
                game_data['home_team']['score'] = teams['home']['score']
                game_scores.append(game_data)
        return game_scores


class NHLTeam(NHL):
    """
    Create NHL team object
    """
    def __init__(self, team=None):
        super().__init__()
        self.team = team
        self.team_id = self._get_team_id(self.team)
        self.info = self._get_team_info(self.team_id)
        self.name = self.info['name']
        self.venue = self.info['venue']['name']
        self.stats = self._get_team_stats(self.team_id)
        self.roster = self._get_team_roster(self.team_id)
        self.schedule = self._get_schedule(self.team_id)
        self.game_results, self.unplayed_games = self._parse_schedule(self.schedule)

    def _get_team_id(self, team=None):
        """
        Get the API id for a provided team
        """
        if not team:
            return None
        if team.lower() not in self._team_list.keys():
            raise NHLTeamException(f"Unrecognized team: {team}")
        team_id = self._team_list.get(team.lower())
        if not team_id:
            raise NHLTeamException(f"Error retrieving ID for {team}")
        return team_id

    def _get_team_info(self, team_id):
        """
        Get general team information
        """
        url = f"{self._base_url}teams/{team_id}"
        data = self._nhl_request(url)
        if data:
            team_info = data['teams'][0]
            return team_info

    def _get_team_stats(self, team_id):
        """
        Get team stats. Return team stats object
        """
        url = f"{self._base_url}teams/{team_id}?expand=team.stats"
        data = self._nhl_request(url)
        return data['teams'][0]

    def _get_team_roster(self, team_id):
        """
        Get team roster. Return list of player objects
        """
        url = f"{self._base_url}teams/{team_id}/roster"
        data = self._nhl_request(url)
        player_list = data['roster']
        return player_list

    def _get_schedule(self, team_id, season='20182019'):
        """
        Get team schedule. Return list of game objects
        """
        url = f"{self._base_url}schedule?teamId={team_id}&season={season}"
        data = self._nhl_request(url)
        game_list = data['dates']
        return game_list


class NHLPlayer(NHL):
    """
    Create an NHL player object
    """
    def __init__(self, player=None):
        super().__init__()
        self.player = player
        self.players = redis.StrictRedis(host='jal_redis.backend', port=6379, db=0)
        self.player_id = self._get_player_id(self.player)
        self.info = self._get_player_info(self.player_id)
        self.season_stats = self._get_season_stats(self.player_id)
        self.career_stats = self._get_career_stats(self.player_id)

    def _get_player_id(self, player):
        if not player:
            raise NHLPlayerException("Missing required param player. Example NHLPlayer('brad marchand')")
        player = self.players.get(player)
        if not player:
            raise NHLPlayerException(f"Player Not Found {player}")
        return player.decode()

    def _get_player_info(self, player_id):
        """
        Get individual stats for a player
        """
        url = f"{self._base_url}people/{player_id}"
        data = self._nhl_request(url)
        if data:
            info = data['people'][0]
            return info

    def _get_season_stats(self, player_id, season=None):
        """
        Get individual stats for a player
        """
        player_info = self._get_player_info(player_id)
        team = player_info['currentTeam']['id']
        if not season:
            season = '20182019'
        endpoint = f"/stats?stats=statsSingleSeason&season={season}"
        url = f"{self._base_url}people/{player_id}{endpoint}"
        data = self._nhl_request(url)
        if data:
            stats = data['stats'][0]['splits'][0]
            stats['team'] = team
            return stats

    def _get_career_stats(self, player_id):
        """
        Get career stats for a player
        """
        endpoint = "stats?stats=yearByYear"
        url = f"{self._base_url}people/{player_id}/{endpoint}"
        data = self._nhl_request(url)
        if data:
            seasons = data['stats'][0]['splits']
            return seasons


def main():
    """
    Main function
    """
    if sys.argv[1]:
        team = sys.argv[1]
        team = NHLTeam(team)
        print(json.dumps(team.game_results))
    else:
        nhl = NHL()
        standings = nhl.standings
        print(json.dumps(standings, indent=2))
    # print(json.dumps(standings['teams'][0]['stats'], indent=4))
    # games = celtics.completed_games
    # for game in games:
    #    print(json.dumps(game, indent=4))


if __name__ == '__main__':
    main()
