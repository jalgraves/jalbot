import aiohttp
import asyncio
import base64
import datetime
import json  # noqa
import logging
import os
import requests

from utils.BotTools import get_config


class NFLRequestException(Exception):
    """Base class for NFL request exceptions"""
    pass


class NFL:
    """
    NFL Games object
    """
    def __init__(self, team=None, player=None):
        logging.info("NFL GAMES")
        self.date = datetime.datetime.now()
        self.base_url = 'https://api.mysportsfeeds.com/v1.2/pull/nfl/'
        self.session = requests.session()
        self.league_schedule = self.nfl_schedule()
        self.upcoming_games = self.get_games_by_week()
        self.nfl_config = get_config('nfl_config.json')
        self.league_game_results = []
        self.recent_league_games = self.get_most_recent_games()
        self.loop = asyncio.new_event_loop()
        self.loop.run_until_complete(self.gather_league_game_results())

        if team:
            self.team_abbreviation = self.nfl_config['abbreviations'].get(team)
            self.team_schedule = self.get_team_schedule(self.team_abbreviation)
            self.loop.run_until_complete(self.schedule_parser())
            self.team_game_results = []
            self.team_stats = self.get_team_stats(self.team_abbreviation)
            self.loop.run_until_complete(self.gather_team_game_results())
            self.loop.close()

    async def schedule_parser(self):
        logging.info("Running looop runner")
        get_played_games = asyncio.create_task(self.played_games())
        get_unplayed_games = asyncio.create_task(self.unplayed_games())
        # get_recent_league_games = asyncio.create_task(self.get_most_recent_games())
        tasks = [
            get_played_games,
            get_unplayed_games
            # get_recent_league_games
        ]
        await asyncio.gather(*tasks)

    def get_most_recent_games(self):
        previous_finished_week = int(self.upcoming_week) - 1
        games = self.get_games_by_week(week=str(previous_finished_week))
        return games

    def data_request(self, url):
        """
        Request data from Mysportsfeeds API
        """
        logging.info(f"URL | {url}")
        api_key = os.environ.get('MYSPORTSFEEDS_API_KEY')
        password = os.environ.get('MYSPORTSFEEDS_PASSWORD')
        byte_string = base64.b64encode('{}:{}'.format(api_key, password).encode('utf-8'))
        headers = {
            "Authorization": f"Basic {byte_string.decode('ascii')}"
        }
        session = requests.session()
        request = session.get(url, headers=headers, verify=False)
        logging.info(request.status_code)
        if request.status_code != 200:
            logging.error(request.status_code)
            logging.error(request.content)
            raise NFLRequestException('Error with Mysportsfeeds API request')
        data = request.json()
        return data

    def nfl_schedule(self):
        """
        Get NFL season schedule
        """
        url = f"{self.base_url}2018-regular/full_game_schedule.json"
        data = self.data_request(url)
        if data:
            schedule = data['fullgameschedule']['gameentry']
            return schedule

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

    def get_game_logs(self, team):
        """
        Get box scores from previously played games
        """
        url = f"https://api.mysportsfeeds.com/v1.2/pull/nfl/{self.season}-regular/team_gamelogs.json?team={team}"
        data = self.data_request(url)
        game_logs = data['teamgamelogs']['gamelogs']
        return game_logs

    def get_team_schedule(self, team):
        url = f"{self.base_url}2018-regular/full_game_schedule.json?team={team}"
        data = self.data_request(url)
        schedule = data['fullgameschedule']['gameentry']
        return schedule

    async def played_games(self):
        played_games = []
        for game in self.team_schedule:
            game_date = datetime.datetime.strptime(game['date'], "%Y-%m-%d")
            if self.date > game_date:
                played_games.append(game)

        self.played_games = played_games
        return played_games

    async def unplayed_games(self):
        unplayed_games = []
        for game in self.team_schedule:
            game_date = datetime.datetime.strptime(game['date'], "%Y-%m-%d")
            if self.date < game_date:
                unplayed_games.append(game)

        self.unplayed_games = unplayed_games
        return unplayed_games

    async def gather_team_game_results(self):
        tasks = []
        for game in self.played_games:
            tasks.append(self.loop.create_task(self.fetch_game_results(self.season, game, 'team')))
        # for game in self.recent_league_games:
        #    tasks.append(self.loop.create_task(self.fetch_game_results(self.season, game, 'league')))
        await asyncio.gather(*tasks)

    async def gather_league_game_results(self):
        tasks = []
        for game in self.recent_league_games:
            tasks.append(self.loop.create_task(self.fetch_game_results(self.season, game, 'league')))
        await asyncio.gather(*tasks)

    async def fetch_game_results(self, season, game, type):
        game_id = game['id']
        api_key = os.environ.get('MYSPORTSFEEDS_API_KEY')
        password = os.environ.get('MYSPORTSFEEDS_PASSWORD')
        url = f"{self.base_url}{season}-regular/game_boxscore.json?gameid={game_id}&teamstats=none&playerstats=none"
        byte_string = base64.b64encode('{}:{}'.format(api_key, password).encode('utf-8'))
        headers = {
            "Authorization": f"Basic {byte_string.decode('ascii')}"
        }
        async with aiohttp.ClientSession() as self.session:
            async with self.session.get(url, headers=headers) as response:
                data = await response.json()
                game_score = data['gameboxscore']['quarterSummary']['quarterTotals']
                game['game_score'] = game_score
                if type == 'team':
                    self.team_game_results.append(game)
                elif type == 'league':
                    self.league_game_results.append(game)

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
        data = self.data_request(url)
        stats = data['divisionteamstandings']
        stats['timestamp'] = int(datetime.datetime.now().timestamp())
        with open('stats_cache/team_stats.json', 'w+') as stats_file:
            stats_file.write(json.dumps(stats, indent=2))
        return stats

    def get_team_stats(self, team_abbreviation):
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


def main():
    nfl = NFLGames()
    standings = nfl.get_division_standings()
    print(standings.keys())
    #game = nfl.get_game_results('46169')
    # games = nfl.get_team_schedule('ne')
    # print(json.dumps(game, indent=2))
    # print(games.keys())

    # print(json.dumps(stats, indent=2))
    # sched = nfl.nfl_schedule
    # print(json.dumps(sched, indent=2))


if __name__ == '__main__':
    main()
