import datetime
import json
import os
import requests
import socket
import time

from bs4 import BeautifulSoup

# from utils.BotTools import get_config
def get_config(config_file):
    """
    Get configuration for command
    :return:
    """
    with open('/jalbot/config/{}'.format(config_file), 'r') as f:
        config = json.load(f)
    if 'env' not in config.keys():
        config['env'] = None
    if config['env']:
        for env_var in config['env']:
            config[env_var] = os.environ[env_var]
        del config['env']
    return config


class NFLScrapeException(Exception):
    """Base class for NFLScrape errors"""
    pass


class NFLScrape:
    """
    Create an NFL stats object scraping HTML
    """
    def __init__(self, team, season=None):
        self.team = team
        self.config = get_config('nfl_config.json')
        self.team_abbreviation = self.config['scrape_ids'].get(team)
        self.base_url = 'https://www.pro-football-reference.com/teams/{}/{}.htm#games::none'
        self.season = season
        self.date = datetime.datetime.now()
        self.stats = self.parse_stats()

    @property
    def current_season(self):
        """
        Return the current NFL season
        """
        return datetime.datetime.strftime(self.date, "%Y")

    @property
    def page_content(self):
        """
        Retrieve the page content from pro-football-reference.com
        """
        if not self.season:
            season = self.current_season
        url = self.base_url.format(self.team_abbreviation, season)
        try:
            request = requests.get(url)
        except (socket.gaierror, requests.exceptions.ConnectionError):
            time.sleep(2)
            try:
                request = requests.get(url)
            except requests.exceptions.ConnectionError as err:
                raise NFLScrapeException(f"Error connecting to server: {err}")
        if request.status_code != 200:
            error = f"Error requesting page content: {request.status_code}"
            raise NFLScrapeException(error)
        return request.content

    @property
    def scrape_content(self):
        """
        Scrape the desired content from the page
        """
        page = self.page_content
        soup = BeautifulSoup(page, 'html.parser')
        tables = soup.find_all('table')
        for table in tables:
            attributes = table.attrs
            data = attributes.get('id')
            if data and data == 'team_stats':
                stats_table = table
                break
        return stats_table

    @staticmethod
    def check_parent(element):
        """
        Check the parent element to make sure the correct stats are being scraped
        """
        parent = element.parent
        header = parent.find('th')
        if header.text == 'Team Stats':
            return 'team'
        elif header.text == 'Opp. Stats':
            return 'opponent'
        elif header.text == 'Lg Rank Defense':
            return 'defense_rank'
        elif header.text == 'Lg Rank Offense':
            return 'offense_rank'

    def parse_stats(self):
        stats = self.scrape_content
        stats_list = stats.find_all('td')
        team_stats = {'team': {}, 'opponent': {}, 'ranks': {'offense': {}, 'defense': {}}}
        for stat in stats_list:
            parent = self.check_parent(stat)
            if parent and parent == 'team':
                attributes = stat.attrs
                name = attributes.get('data-stat')
                text = stat.text
                if name and text:
                    team_stats['team'][name] = text
            elif parent and parent == 'opponent':
                attributes = stat.attrs
                name = attributes.get('data-stat')
                text = stat.text
                if name and text:
                    team_stats['opponent'][name] = text
            elif parent and parent == 'offense_rank':
                attributes = stat.attrs
                name = attributes.get('data-stat')
                text = stat.text
                if name and text:
                    team_stats['ranks']['offense'][name] = text
            elif parent and parent == 'defense_rank':
                attributes = stat.attrs
                name = attributes.get('data-stat')
                text = stat.text
                if name and text:
                    team_stats['ranks']['defense'][name] = text
        return team_stats


def main():
    team = NFLScrape('patriots')
    print(json.dumps(team.stats, indent=2))


if __name__ == '__main__':
    main()
