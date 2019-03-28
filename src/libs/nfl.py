import aiohttp
import asyncio
import base64
import datetime
import json  # noqa
import logging
import os
import requests
import socket
import time

from utils.BotTools import get_config
from utils.exceptions import NFLRequestException


class NFL:
    """
    NFL Games object
    """
    def __init__(self, api_version="1.2"):
        self.api_key = os.environ.get('MYSPORTSFEEDS_API_KEY')
        self.version = api_version
        self.password = os.environ.get('MYSPORTSFEEDS_PASSWORD')
        self.date = datetime.datetime.now()
        self.base_url = f"https://api.mysportsfeeds.com/v{self.version}/pull/nfl/"
        self.session = requests.session()
        self.league_schedule = self.get_schedule()
        self.upcoming_games = self.get_games_by_week()
        self.config = get_config('nfl_config.json')
        self.league_game_results = []
        self.played_games = []
        self.unplayed_games = []
        self.league_played_games = []
        self.league_unplayed_games = []
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.parse_league_games())
        self.loop.run_until_complete(self.gather_league_data())

    def __repr__(self):
        return f"{self.league_schedule}"

    @property
    def recent_league_games(self):
        last_completed_week = int(self.upcoming_week) - 1
        return self.get_games_by_week(week=str(last_completed_week))

    @property
    def upcoming_week(self):
        """
        Get the upcoming week for the NFL
        """
        for game in self.league_schedule:
            game_date = datetime.datetime.strptime(game['date'], "%Y-%m-%d")
            if game_date >= self.date:
                week = game['week']
                break
        return week

    @property
    def season(self):
        """
        Return current season
        """
        return datetime.datetime.strftime(self.date, "%Y")

    def _headers(self, password=None):
        """
        Authroization HEADERS for Mysportsfeeds API requests
        """
        if not password:
            pwd = self.password
        else:
            pwd = password
        byte_string = base64.b64encode('{}:{}'.format(self.api_key, pwd).encode('utf-8'))
        headers = {
            "Authorization": f"Basic {byte_string.decode('ascii')}"
        }
        return headers

    @property
    def standings(self):
        standings = {
            'conference': {
                'AFC': {},
                'NFC': {}
            },
            'division': {
                'AFC East': {},
                'AFC North': {},
                'AFC South': {},
                'AFC West': {},
                'NFC East': {},
                'NFC North': {},
                'NFC South': {},
                'NFC West': {}
            },
            'league': {},
            'records': {}
        }
        for team in self.standings_data:
            name = team['team']['name']
            record = team['stats']['standings']
            division_name = team['divisionRank']['divisionName']
            conference_name = team['conferenceRank']['conferenceName']
            division_rank = team['divisionRank']['rank']
            conference_rank = team['conferenceRank']['rank']
            league_rank = team['overallRank']['rank']
            standings['conference'][conference_name][name] = conference_rank
            standings['division'][division_name][name] = division_rank
            standings['league'][name] = league_rank
            standings['records'][name] = record
        return standings

    async def league_schedule_parser(self):
        # self.league_schedule = await asyncio.gather([self.loop.create_task(self.get_schedule(self.team_abbreviation))])
        parse_games = asyncio.create_task(self.parse_league_games())
        # get_recent_league_games = asyncio.create_task(self.get_most_recent_games())
        tasks = [
            parse_games
            # get_recent_league_games
        ]
        await asyncio.gather(*tasks)

    async def parse_league_games(self):
        """
        From an NFL team's schedule separate games that have been completed and
        games that haven't been played yet
        """
        for game in self.upcoming_games:
            game_date = datetime.datetime.strptime(game['date'], "%Y-%m-%d")
            if self.date > game_date:
                self.league_played_games.append(game)
            else:
                self.league_unplayed_games.append(game)

    def api_request(self, url):
        """
        Request data from Mysportsfeeds API
        """
        logging.info(f"URL | {url}")
        session = requests.session()
        try:
            request = session.get(url, headers=self._headers(), verify=False)
        except socket.gaierror:
            time.sleep(1)
            request = session.get(url, headers=self._headers(), verify=False)
        except requests.exceptions.ConnectionError:
            time.sleep(2)
            request = session.get(url, headers=self._headers(), verify=False)
        if request.status_code != 200:
            raise NFLRequestException(f"{request.status_code} Error with Mysportsfeeds API request")
        data = request.json()
        return data

    def get_schedule(self, team_abbreviation=None):
        """
        Get NFL season schedule
        """
        if not team_abbreviation:
            url = f"{self.base_url}2018-regular/full_game_schedule.json"
        else:
            url = f"{self.base_url}2018-regular/full_game_schedule.json?team={team_abbreviation}"
        data = self.api_request(url)
        if data:
            schedule = data['fullgameschedule']['gameentry']
            return schedule

    def get_games_by_week(self, week=None):
        """
        Get games for the upcoming week
        """
        games = []
        if not week:
            week = self.upcoming_week
        schedule = self.league_schedule
        for game in schedule:
            if game['week'] == week:
                games.append(game)
        return games

    def league_scores(self):
        """
        Get current league game scores
        """
        date = datetime.datetime.strftime(self.date, "%Y%m%d")
        url = f"{self.base_url}{self.season}-regular/scoreboard.json?fordate={date}"
        scores = self.api_request(url)
        return scores['scoreboard']['gameScore']

    async def gather_league_data(self):
        tasks = [self.loop.create_task(self.fetch_standings())]
        if self.league_played_games:
            for game in self.league_played_games:
                tasks.append(self.loop.create_task(self.fetch_game_results(self.season, game, 'league')))
        else:
            for game in self.recent_league_games:
                tasks.append(self.loop.create_task(self.fetch_game_results(self.season, game, 'league')))
        await asyncio.gather(*tasks)

    async def fetch_game_results(self, season, game, type):
        url = f"{self.base_url}{season}-regular/game_boxscore.json?gameid={game['id']}&playerstats=none"
        logging.info(url)
        async with aiohttp.ClientSession() as self.session:
            async with self.session.get(url, headers=self._headers()) as response:
                try:
                    data = await response.json()
                except aiohttp.client_exceptions.ContentTypeError as err:
                    if 'status' in dir(response):
                        logging.info(response.status)
                    logging.error(f"Error retrieving data from Mysportsfeeds API\n\n{err}")
                    data = None
                    pass
                    # raise NFLRequestException(f"Error retrieving data from Mysportsfeeds API\n\n{response.status}\n{response.reason}\n{response.raw_headers}\n{response.content}")
            if data:
                game_score = data['gameboxscore']['quarterSummary']['quarterTotals']
                game['game_score'] = game_score
                if type == 'team':
                    self.team_game_results.append(game)
                elif type == 'league':
                    self.league_game_results.append(game)

    async def fetch_standings(self):
        url = "https://api.mysportsfeeds.com/v2.0/pull/nfl/2018-regular/standings.json"
        async with aiohttp.ClientSession() as self.session:
            async with self.session.get(url, headers=self._headers('MYSPORTSFEEDS')) as response:
                try:
                    data = await response.json()
                except aiohttp.client_exceptions.ContentTypeError:
                    logging.error("Error retrieving data from Mysportsfeeds API")
                    raise NFLRequestException(f"Error retrieving data from Mysportsfeeds API")
            if data:
                teams_list = data['teams']
                self.standings_data = teams_list

    def parse_division_standings(self):
        stats = self.fetch_team_stats()
        divisions = stats['division']
        standings = []
        for division in divisions:
            div = {}
            division_name = division['@name'][4:]
            div['name'] = division_name
            div['teams'] = []
            for i in division['teamentry']:
                div_team = {}
                team = i['team']
                div_team['name'] = team['Name']
                div_team['rank'] = i['rank']
                wins = i['stats']['Wins']['#text']
                losses = i['stats']['Losses']['#text']
                ties = i['stats']['Ties']['#text']
                div_team['record'] = f"{wins} - {losses} - {ties}"
                div['teams'].append(div_team)
            standings.append(div)
        return standings

    def fetch_team_stats(self):
        stats = self.check_data_cache('nfl_team_stats.json')
        if stats:
            return stats
        url = 'https://api.mysportsfeeds.com/v1.2/pull/nfl/2018-regular/division_team_standings.json'
        data = self.api_request(url)
        stats = data['divisionteamstandings']
        stats['timestamp'] = int(datetime.datetime.now().timestamp())
        with open('stats_cache/team_stats.json', 'w+') as stats_file:
            stats_file.write(json.dumps(stats, indent=2))
        return stats

    def check_data_cache(self, file_name):
        try:
            with open(f'stats_cache/{file_name}', 'r') as read_file:
                data = json.load(read_file)
        except FileNotFoundError:
            data = None
            return data

        data_age = data['timestamp'] + 43200
        if data_age < int(self.date.timestamp()):
            data = None
        return data

    def live_scores(self):
        url = f"{self._base_url}2018-regular/date/20181126/games.json"
        data = self._api_request(url)
        logging.info(json.dumps(data, indent=2))
        pass


class NFLLeague(NFL):
    def __init__(self):
        super().__inii__(self)

    def live_scores(self):
        url = f"{self._base_url}2018-regular/date/20181126/games.json"
        data = self._api_request(url)
        logging.info(json.dumps(data, indent=2))
        pass


class NFLTeam(NFL):
    """
    Create NFL team object
    """
    def __init__(self, team=None):
        super().__init__()
        self.team = team
        self.team_abbreviation = self.config['abbreviations'].get(team)
        self.schedule = self.get_schedule(self.team_abbreviation)
        self.game_results = []
        self.team_game_results = []
        self.team_game_stats = []
        self.stats = self.parse_stats(self.team_abbreviation)
        self.loop.run_until_complete(self.schedule_parser())
        self.loop.run_until_complete(self.gather_team_game_results())
        self.loop.run_until_complete(self.gather_team_stats())
        self.loop.close()

    async def schedule_parser(self):
        # parse_games = asyncio.create_task(self.parse_games())
        # game_logs = asyncio.create_task(self.get_game_logs())
        # get_recent_league_games = asyncio.create_task(self.get_most_recent_games())
        # self.schedule = await asyncio.gather([self.loop.create_task(self.get_schedule(self.team_abbreviation))])
        tasks = [
            self.loop.create_task(self.parse_games())
            # game_logs
        ]
        await asyncio.gather(*tasks)

    async def fetch_game_logs(self, team_abbreviation):
        url = f"{self.base_url}{self.season}-regular/team_gamelogs.json?team={team_abbreviation}"
        async with aiohttp.ClientSession() as self.session:
            async with self.session.get(url, headers=self._headers()) as response:
                data = await response.json()
                return data

    async def fetch_team_game_results(self, season, game):
        url = f"{self.base_url}{season}-regular/game_boxscore.json?gameid={game['id']}&playerstats=none"
        async with aiohttp.ClientSession() as self.session:
            async with self.session.get(url, headers=self._headers()) as response:
                try:
                    data = await response.json()
                except aiohttp.client_exceptions.ContentTypeError:
                    logging.error("Error retrieving data from Mysportsfeeds API")
                    data = None
                    pass
                if data:
                    quarter_summary = data['gameboxscore']['quarterSummary']
                    game_score = data['gameboxscore']['quarterSummary']['quarterTotals']
                    away_stats = data['gameboxscore']['awayTeam']['awayTeamStats']
                    home_stats = data['gameboxscore']['homeTeam']['homeTeamStats']
                    game['quarter_summary'] = quarter_summary
                    game['game_score'] = game_score
                    game['awayTeam']['stats'] = away_stats
                    game['homeTeam']['stats'] = home_stats
                    self.team_game_results.append(game)

    async def gather_team_game_results(self):
        """
        Create tasks to gather scores for individual games from Mysportsfeeds API
        """
        tasks = []
        for game in self.played_games:
            tasks.append(self.loop.create_task(self.fetch_team_game_results(self.season, game)))
        await asyncio.gather(*tasks)
        await asyncio.gather(self.parse_game_stats())

    async def gather_team_stats(self):
        tasks = [
            self.loop.create_task(self.offense_points_by_quarter()),
            self.loop.create_task(self.defense_points_by_quarter()),
            self.loop.create_task(self.parse_road_record()),
            self.loop.create_task(self.parse_home_record()),
            self.loop.create_task(self.parse_turnovers()),
            self.loop.create_task(self.parse_totals()),
            self.loop.create_task(self.parse_defensive_stats())
        ]
        await asyncio.gather(*tasks)

    async def parse_totals(self):
        self.penalties = self.stats['Penalties']
        self.penalty_yards = self.stats['PenaltyYds']
        self.total_yards_gained = self.stats['OffenseYds']
        self.yards_per_play = self.stats['OffenseAvgYds']
        self.offense_plays = self.stats['OffensePlays']
        self.third_downs = self.stats['ThirdDowns']
        self.third_down_attempts = self.stats['ThirdDownsAtt']
        self.third_down_percentage = self.stats['ThirdDownsPct']
        self.pass_attempts = self.stats['PassAttempts']
        self.pass_completions = self.stats['PassCompletions']
        self.pass_yards = self.stats['PassNetYards']
        self.pass_yards_per_attempt = self.stat_trim(int(self.pass_yards) / int(self.pass_attempts))
        self.games_played = int(self.stats['GamesPlayed'])
        self.touchdowns_scored = self.stats['TotalTD']
        self.points_for = self.stats['PointsFor']
        self.points_against = self.stats['PointsAgainst']
        self.first_down_total = self.stats['FirstDownsTotal']
        self.first_down_pass = self.stats['FirstDownsPass']
        self.first_down_rush = self.stats['FirstDownsRush']
        self.rush_yards = self.stats['RushYards']
        self.rush_attempts = self.stats['RushAttempts']
        self.rush_average = self.stats['RushAverage']
        self.rush_touchdowns = self.stats['RushTD']
        self.receptions = self.stats['Receptions']
        self.offense_sacks = self.stats['PassSacks']
        self.defense_sacks = self.stats['Sacks']
        self.points_diff = int(self.points_for) - int(self.points_against)
        self.offense_yards_per_game = self.stat_trim(int(self.total_yards_gained) / self.games_played)

    async def get_game_logs(self):
        game_logs = await self.fetch_game_logs(self.team_abbreviation)
        self.game_logs = game_logs['teamgamelogs']['gamelogs']

    async def parse_game_stats(self):
        team = self.team_abbreviation.upper()
        for game in self.team_game_results:
            game_stats = {'offense': {}, 'defense': {}}
            home_team = game['homeTeam']['Abbreviation']
            away_team = game['awayTeam']['Abbreviation']
            game_stats['week'] = game['week']
            game_stats['date'] = game['date']
            game_stats['time'] = game['time']
            if home_team == team:
                game_stats['gameType'] = 'homeGame'
                game_stats['opponent'] = away_team
                game_stats['pointsFor'] = int(game['homeTeam']['stats']['PointsFor']['#text'])
                game_stats['pointsAgainst'] = int(game['homeTeam']['stats']['PointsAgainst']['#text'])
                game_stats['interceptionsThrown'] = int(game['homeTeam']['stats']['PassInt']['#text'])
                game_stats['interceptions'] = int(game['homeTeam']['stats']['Interceptions']['#text'])
                game_stats['fumblesLost'] = int(game['homeTeam']['stats']['FumLost']['#text'])
                game_stats['fumblesRecovered'] = int(game['homeTeam']['stats']['FumOppRec']['#text'])
                game_stats['offense']['yardsGained'] = int(game['homeTeam']['stats']['OffenseYds']['#text'])
                game_stats['defense']['yardsAllowed'] = int(game['awayTeam']['stats']['OffenseYds']['#text'])
                game_stats['defense']['plays'] = int(game['awayTeam']['stats']['OffensePlays']['#text'])
                # game_stats['defense']['third_down_attempts'] = int(game['awayTeam']['stats']['ThirdDownsAtt']['#text'])
                # game_stats['defense']['third_down_conversions'] = int(game['awayTeam']['stats']['ThirdDowns']['#text'])
                game_stats['offense']['1stQuarterPoints'] = int(game['quarter_summary']['quarter'][0]['homeScore'])
                game_stats['defense']['1stQuarterPoints'] = int(game['quarter_summary']['quarter'][0]['awayScore'])
                game_stats['offense']['2ndQuarterPoints'] = int(game['quarter_summary']['quarter'][1]['homeScore'])
                game_stats['defense']['2ndQuarterPoints'] = int(game['quarter_summary']['quarter'][1]['awayScore'])
                game_stats['offense']['3rdQuarterPoints'] = int(game['quarter_summary']['quarter'][2]['homeScore'])
                game_stats['defense']['3rdQuarterPoints'] = int(game['quarter_summary']['quarter'][2]['awayScore'])
                game_stats['offense']['4thQuarterPoints'] = int(game['quarter_summary']['quarter'][3]['homeScore'])
                game_stats['defense']['4thQuarterPoints'] = int(game['quarter_summary']['quarter'][3]['awayScore'])
            else:
                game_stats['gameType'] = 'roadGame'
                game_stats['opponent'] = home_team
                game_stats['pointsFor'] = int(game['awayTeam']['stats']['PointsFor']['#text'])
                game_stats['pointsAgainst'] = int(game['awayTeam']['stats']['PointsAgainst']['#text'])
                game_stats['interceptionsThrown'] = int(game['awayTeam']['stats']['PassInt']['#text'])
                game_stats['interceptions'] = int(game['awayTeam']['stats']['Interceptions']['#text'])
                game_stats['fumblesLost'] = int(game['awayTeam']['stats']['FumLost']['#text'])
                game_stats['fumblesRecovered'] = int(game['awayTeam']['stats']['FumOppRec']['#text'])
                game_stats['offense']['yardsGained'] = game['awayTeam']['stats']['OffenseYds']['#text']
                game_stats['defense']['yardsAllowed'] = game['homeTeam']['stats']['OffenseYds']['#text']
                game_stats['defense']['plays'] = int(game['homeTeam']['stats']['OffensePlays']['#text'])
                # game_stats['defense']['third_down_attempts'] = int(game['homeTeam']['stats']['ThirdDownsAtt']['#text'])
                # game_stats['defense']['third_down_conversions'] = int(game['homeTeam']['stats']['ThirdDowns']['#text'])
                game_stats['defense']['1stQuarterPoints'] = int(game['quarter_summary']['quarter'][0]['homeScore'])
                game_stats['offense']['1stQuarterPoints'] = int(game['quarter_summary']['quarter'][0]['awayScore'])
                game_stats['defense']['2ndQuarterPoints'] = int(game['quarter_summary']['quarter'][1]['homeScore'])
                game_stats['offense']['2ndQuarterPoints'] = int(game['quarter_summary']['quarter'][1]['awayScore'])
                game_stats['defense']['3rdQuarterPoints'] = int(game['quarter_summary']['quarter'][2]['homeScore'])
                game_stats['offense']['3rdQuarterPoints'] = int(game['quarter_summary']['quarter'][2]['awayScore'])
                game_stats['defense']['4thQuarterPoints'] = int(game['quarter_summary']['quarter'][3]['homeScore'])
                game_stats['offense']['4thQuarterPoints'] = int(game['quarter_summary']['quarter'][3]['awayScore'])
            self.team_game_stats.append(game_stats)

    @staticmethod
    def stat_trim(stat):
        """
        Trim stats with long decimals for better visual presentation
        """
        stat = str(stat)
        if stat[1] == '.' and len(stat) > 4:
            return stat[:4]
        elif len(stat) > 6:
            stat = stat[:6]
        return stat

    async def parse_defensive_stats(self):
        """
        The Mysportsfeeds API doesn't provide totals for defensive plays and
        yardage so this function parses them from the individual game stats
        """
        defense_plays = 0
        defense_yards_allowed = 0  # noqa
        # defense_third_down_attempts = 0  # noqa
        # defense_third_down_conversions = 0  # noqa

        for game in self.team_game_stats:
            defense_plays += game['defense']['plays']
            defense_yards_allowed += int(game['defense']['yardsAllowed'])  # noqa
            # defense_third_down_attempts = int(game['defense']['third_down_attempts'])  # noqa
            # defense_third_down_conversions = int(game['defense']['third_down_conversions'])  # noqa

        self.defense_plays = defense_plays
        self.total_yards_allowed = defense_yards_allowed
        self.defense_yards_per_play = self.stat_trim(defense_yards_allowed / defense_plays)
        self.defense_yards_per_game = self.stat_trim(defense_yards_allowed / len(self.team_game_stats))
        # self.defense_third_down_attempts = defense_third_down_attempts
        # self.defense_third_down_conversions = defense_third_down_conversions
        # self.defense_third_down_percentage = self.stat_trim(defense_third_down_attempts / defense_third_down_attempts)

    async def parse_turnovers(self):
        turnovers = 0
        takeaways = 0
        for game in self.team_game_stats:
            turnovers += game['interceptionsThrown']
            turnovers += game['fumblesLost']
            takeaways += game['fumblesRecovered']
            takeaways += game['interceptions']
        self.turnovers = turnovers
        self.takeaways = takeaways
        self.turnover_diff = self.takeaways - self.turnovers

    async def parse_road_record(self):
        """
        Parse team's road wins and losses
        """
        road_wins = 0
        road_losses = 0
        road_ties = 0
        for game in self.team_game_stats:
            if game['gameType'] == 'roadGame':
                if game['pointsFor'] > game['pointsAgainst']:
                    road_wins += 1
                elif game['pointsFor'] < game['pointsAgainst']:
                    road_losses += 1
                else:
                    road_ties += 1
        self.road_record = f"{road_wins}-{road_losses}-{road_ties}"

    async def parse_home_record(self):
        """
        Parse team's road wins and losses
        """
        wins = 0
        losses = 0
        ties = 0
        for game in self.team_game_stats:
            if game['gameType'] == 'homeGame':
                if game['pointsFor'] > game['pointsAgainst']:
                    wins += 1
                elif game['pointsFor'] < game['pointsAgainst']:
                    losses += 1
                else:
                    ties += 1
        self.home_record = f"{wins}-{losses}-{ties}"

    async def offense_points_by_quarter(self):
        """
        Get total points scored in each quarter
        """
        first_quarter = []
        second_quarter = []
        third_quarter = []
        fourth_quarter = []
        for game in self.team_game_stats:
            first_quarter.append(game['offense']['1stQuarterPoints'])
            second_quarter.append(game['offense']['2ndQuarterPoints'])
            third_quarter.append(game['offense']['3rdQuarterPoints'])
            fourth_quarter.append(game['offense']['4thQuarterPoints'])
        self.first_quarter_points_scored = sum(first_quarter)
        self.second_quarter_points_scored = sum(second_quarter)
        self.third_quarter_points_scored = sum(third_quarter)
        self.fourth_quarter_points_scored = sum(fourth_quarter)

    async def defense_points_by_quarter(self):
        """
        Get total points allowed in each quarter
        """
        first_quarter = []
        second_quarter = []
        third_quarter = []
        fourth_quarter = []
        for game in self.team_game_stats:
            first_quarter.append(game['defense']['1stQuarterPoints'])
            second_quarter.append(game['defense']['2ndQuarterPoints'])
            third_quarter.append(game['defense']['3rdQuarterPoints'])
            fourth_quarter.append(game['defense']['4thQuarterPoints'])
        self.first_quarter_points_allowed = sum(first_quarter)
        self.second_quarter_points_allowed = sum(second_quarter)
        self.third_quarter_points_allowed = sum(third_quarter)
        self.fourth_quarter_points_allowed = sum(fourth_quarter)

    async def parse_games(self):
        """
        From an NFL team's schedule separate games that have been completed and
        games that haven't been played yet
        """
        for game in self.schedule:
            game_date = datetime.datetime.strptime(game['date'], "%Y-%m-%d")
            if self.date > game_date:
                self.played_games.append(game)
            else:
                self.unplayed_games.append(game)

    def fetch_team_stats(self):
        """
        Get team stats from Mysportsfeeds API
        """
        stats = self.check_data_cache('nfl_team_stats.json')
        if stats:
            return stats
        url = f"{self.base_url}current/division_team_standings.json"
        data = self.api_request(url)
        stats = data['divisionteamstandings']
        stats['timestamp'] = int(datetime.datetime.now().timestamp())
        with open('stats_cache/team_stats.json', 'w+') as stats_file:
            stats_file.write(json.dumps(stats, indent=2))
        return stats

    def parse_stats(self, team_abbreviation):
        stats = self.fetch_team_stats()
        divisions = stats['division']
        for division in divisions:
            for i in division['teamentry']:
                if i['team']['Abbreviation'] == team_abbreviation.upper():
                    team_stats = i['stats']
                    break
        filtered_stats = {}
        for k, v in team_stats.items():
            if isinstance(v, dict):
                stat_value = v.get('#text')
                if stat_value:
                    filtered_stats[k] = stat_value
        return filtered_stats


class NFLPlayer(NFL):
    """
    Create NFL player object
    """
    def __init__(self, player, season=None):
        super().__init__(self, player)
        self.player = player

    def get_season_game_stats(self):
        """
        Get player stats from individual games
        """
        pass

    def get_career_stats(self):
        """
        Get player's career stats
        """
        pass

    def get_player_rankings(self, category):
        """
        Get player rankings for particular stats category
        """
        pass

def main():
    api_key = os.environ.get('MYSPORTSFEEDS_API_KEY')
    pwd = 'MYSPORTSFEEDS'
    byte_string = base64.b64encode('{}:{}'.format(api_key, pwd).encode('utf-8'))
    headers = {
        "Authorization": f"Basic {byte_string.decode('ascii')}"
    }
    url = 'https://api.mysportsfeeds.com/v2.0/pull/nfl/2018-regular/date/20181126/games.json'
    req = requests.get(url, headers=headers, verify=False)
    print(req.status_code)
    print(json.dumps(req.json(), indent=2))

    #game = nfl.get_game_results('46169')
    # games = nfl.get_team_schedule('ne')
    # print(json.dumps(game, indent=2))
    # print(games.keys())

    # print(json.dumps(stats, indent=2))
    # sched = nfl.nfl_schedule
    # print(json.dumps(sched, indent=2))


if __name__ == '__main__':
    main()
