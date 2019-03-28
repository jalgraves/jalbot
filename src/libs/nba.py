import datetime
import json
import logging
import requests

from collections import namedtuple
from datetime import timedelta
from pytz import timezone
from pymemcache.client.base import Client
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from utils.BotTools import get_config
from utils.exceptions import NBAException

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


BASE_URL = 'https://stats.nba.com/stats/'


CONFIG = get_config('nba.json')


def json_serializer(key, value):
    if type(value) == str:
        return value, 1
    return json.dumps(value), 2


def json_deserializer(key, value, flags):
    if flags == 1:
        return value.decode('utf-8')
    if flags == 2:
        return json.loads(value.decode('utf-8'))
    raise Exception("Unknown serialization format")


CACHE_HOST = ('jal_memcache.backend', 11211)
CACHE = Client(CACHE_HOST, serializer=json_serializer, deserializer=json_deserializer)


def fetch_data(session, url, params):
    """
    Fetch data from stats.nba.com API
    """
    user_agent = [
        'Mozilla/5.0 (Windows NT 6.2; WOW64)',
        'AppleWebKit/537.36 (KHTML, like Gecko)',
        'Chrome/57.0.2987.133 Safari/537.36'
    ]

    headers = {
        'user-agent': (" ".join(user_agent)),
        'Dnt': ('1'),
        'Accept-Encoding': ('gzip, deflate, sdch'),
        'Accept-Language': ('en'),
        'origin': ('http://stats.nba.com')
    }

    try:
        request = session.get(url, headers=headers, params=params, verify=False, timeout=5)
    except requests.exceptions.Timeout as err:
        err_message = [
            'Unable to connect to stats.nba.com API.',
            'Connection timed out'
        ]
        raise NBAException("\n".join(err_message))
    except requests.exceptions.ConnectionError:
        request = session.get(url, headers=headers, params=params, verify=False)
    print(request.status_code)
    if request.status_code == 200:
        data = request.json()
        #logging.info(json.dumps(data, indent=2))
        # for i in data['resultSets']:
        #    logging.info(i['name'])
        return data['resultSets']
    else:
        print(request.status_code)


class NBA:
    """
    Create NBA team object
    """
    def __init__(self):
        self._session = requests.session()
        self._date = datetime.datetime.now(timezone('US/Eastern'))


class NBALeague(NBA):
    """
    NBA League
    """
    def __init__(self):
        super().__init__()
        self._team_ids = CONFIG['ids']
        self.team_records = self.nba_records()
        self.overall_standings = self.team_win_percentages()
        self.eastern_conference_standings = self.east_win_percentages()
        self.western_conference_standings = self.west_win_percentages()

    def recent_games(self):
        date = (self._date - timedelta(1)).strftime("%m/%d/%Y")
        return self._get_games_data(date)

    def recent_scoress(self):
        games = []
        recent_games = self.recent_games()
        headers = recent_games[1]['headers']
        game_sets = recent_games[1]['rowSet']
        game_scores = {}
        for game in game_sets:
            games.append(list(zip(headers, game)))
        count = 1
        while count <= 2:
            for game in games:
                game_id = self._get_data(game, 'GAME_ID')
                team_id = self._get_data(game, 'TEAM_ID')
                points = self._get_data(game, 'PTS')
                game_scores[game_id] = {}
                game_scores[game_id][team_id] = points
            count += 1
        return game_scores

    def recent_scores(self):
        games = []
        if self.todays_games.live or self.todays_games.final:
            return self.todays_games.live + self.todays_games.final
        games_data = self.recent_games()
        game_headers = games_data[0]['headers']
        game_sets = games_data[0]['rowSet']
        for game in game_sets:
            game_info = list(zip(game_headers, game))
            home_id = self._get_data(game_info, 'HOME_TEAM_ID')
            visitor_id = self._get_data(game_info, 'VISITOR_TEAM_ID')
            game_data = {}
            game_data['id'] = self._get_data(game_info, 'GAME_ID')
            game_data['home_team'] = self._team_ids.get(home_id)
            game_data['away_team'] = self._team_ids.get(visitor_id)
            score_headers = games_data[1]['headers']
            score_sets = games_data[1]['rowSet']
            game_scores = []
            for score in score_sets:
                game_scores.append(list(zip(score_headers, score)))
            for score in game_scores:
                game_id = self._get_data(score, 'GAME_ID')
                team_id = self._get_data(score, 'TEAM_ID')
                points = self._get_data(score, 'PTS')
                if game_id == game_data['id']:
                    if team_id == home_id:
                        game_data['home_team_score'] = points
                    elif team_id == visitor_id:
                        game_data['away_team_score'] = points
            games.append(game_data)
        logging.info(games)
        return games

    def nba_records(self):
        nba_data = {}
        east = self._conference_record_data('east')
        west = self._conference_record_data('west')
        for i in east.keys():
            wins = east[i]['wins']
            losses = east[i]['losses']
            record = f"{wins}-{losses}"
            nba_data[i] = record
        for i in west.keys():
            wins = west[i]['wins']
            losses = west[i]['losses']
            record = f"{wins}-{losses}"
            nba_data[i] = record
        return nba_data

    def team_win_percentages(self):
        win_percentages = {}
        for k, v in self.eastern_conference.items():
            win_percentages[k] = v['win_percentage']
        for k, v in self.western_conference.items():
            win_percentages[k] = v['win_percentage']
        return win_percentages

    def east_win_percentages(self):
        win_percentages = {}
        for k, v in self.eastern_conference.items():
            win_percentages[k] = v['win_percentage']
        return win_percentages

    def west_win_percentages(self):
        win_percentages = {}
        for k, v in self.western_conference.items():
            win_percentages[k] = v['win_percentage']
        return win_percentages

    @staticmethod
    def get_team_id(team):
        team_ids = CONFIG['names_to_id']
        team_id = team_ids.get(team)
        return team_id

    @property
    def eastern_conference(self):
        return self._conference_record_data('east')

    @property
    def western_conference(self):
        return self._conference_record_data('west')

    @property
    def todays_games(self):
        """
        Fetch data from stats.nba.com and create list containing an object
        for each game being played today
        """
        unplayed_games = []
        live_games = []
        finished_games = []
        games_data = self._get_games_data()
        game_headers = games_data[0]['headers']
        game_sets = games_data[0]['rowSet']
        for game in game_sets:
            game_info = list(zip(game_headers, game))
            status = self._get_data(game_info, 'GAME_STATUS_ID')
            home_id = self._get_data(game_info, 'HOME_TEAM_ID')
            visitor_id = self._get_data(game_info, 'VISITOR_TEAM_ID')
            logging.info(status)
            game_data = {}
            game_data['id'] = self._get_data(game_info, 'GAME_ID')
            game_data['game_date'] = self._get_data(game_info, 'GAME_DATE_EST')
            game_data['game_time'] = self._get_data(game_info, 'GAME_STATUS_TEXT')
            game_data['home_record'] = self.record(home_id)
            game_data['home_team'] = self._team_ids.get(home_id)
            game_data['away_record'] = self.record(visitor_id)
            game_data['away_team'] = self._team_ids.get(visitor_id)
            if status == '1':
                unplayed_games.append(game_data)
            elif status == '2' or status == '3':
                score_headers = games_data[1]['headers']
                score_sets = games_data[1]['rowSet']
                game_scores = []
                for score in score_sets:
                    game_scores.append(list(zip(score_headers, score)))
                for score in game_scores:
                    game_id = self._get_data(score, 'GAME_ID')
                    team_id = self._get_data(score, 'TEAM_ID')
                    points = self._get_data(score, 'PTS')
                    if game_id == game_data['id']:
                        if team_id == home_id:
                            game_data['home_team_score'] = points
                        elif team_id == visitor_id:
                            game_data['away_team_score'] = points
                if status == '2':
                    live_games.append(game_data)
                elif status == '3':
                    finished_games.append(game_data)
        Games = namedtuple('Status', ['unplayed', 'live', 'final'])
        games_info = Games(unplayed=unplayed_games, live=live_games, final=finished_games)
        CACHE.set(game_data['id'], game_data)
        return games_info

    def record(self, team_id):
        """
        Get an NBA teams record with a team name or ID
        """
        team = str(team_id)
        if team not in self._team_ids.keys():
            team = self.get_team_id(team)
        if not team:
            raise NBAException('Invalid name or team ID')

        record = self.team_records.get(team)
        return record

    def _get_games_data(self, date=None):
        """
        Fetch data from stats.nba.com for the days games
        The API returns all games for the calendar day along with their state
        (1 for unplayed, 2 for ongoing live, 3 for completed).
        """
        endpoint = 'scoreboard'
        url = f"{BASE_URL}{endpoint}/"
        # if no date is provided get data for the current days games
        if not date:
            date = datetime.datetime.strftime(self._date, "%m/%d/%Y")
        params = {
            'GameDate': date,
            'LeagueID': '00',
            'DayOffset': '0'
        }
        data = fetch_data(self._session, url, params)
        return data

    def _get_data(self, game_info, data_title):
        """
        Get the data value from the zipped list of row headers (data titles)
        and data points
        """
        for game in game_info:
            header, data = game
            # logging.info(f"{header} {data}")
            if header == data_title:
                data = str(data)
                return data

    def _conference_record_data(self, conference):
        if conference == 'east':
            conference = 'EastConfStandingsByDay'
        else:
            conference = 'WestConfStandingsByDay'
        conference_data = {}
        for i in self._get_games_data():
            if i['name'] == conference:
                headers = i['headers']
                game_sets = i['rowSet']
                for game in game_sets:
                    game_data = list(zip(headers, game))
                    team_data = {}
                    team_data['id'] = self._get_data(game_data, 'TEAM_ID')
                    team_data['name'] = self._get_data(game_data, 'TEAM')
                    team_data['games_played'] = self._get_data(game_data, 'G')
                    team_data['wins'] = self._get_data(game_data, 'W')
                    team_data['losses'] = self._get_data(game_data, 'L')
                    team_data['win_percentage'] = self._get_data(game_data, 'W_PCT')
                    team_data['conference'] = self._get_data(game_data, 'CONFERENCE')
                    team_data['home_record'] = self._get_data(game_data, 'HOME_RECORD')
                    team_data['road_record'] = self._get_data(game_data, 'ROAD_RECORD')
                    conference_data[team_data['id']] = team_data
        return conference_data

    def league_leaders(self):
        endpoint = 'leagueleaders'
        params = {
            'LeagueID': '00',
            'StatCategory': 'Scoring',
            'Season': '2018-19',
            'PerMode': 'PerGame',
            'Scope': 'RS',
            'SeasonType': 'Regular Season',
        }
        return endpoint, params


def main():
    nba = NBALeague()
    games = nba.todays_games
    print(json.dumps(games, indent=2))
    # print(json.dumps(games['resultSets'][0], indent=2))


if __name__ == '__main__':
    main()
