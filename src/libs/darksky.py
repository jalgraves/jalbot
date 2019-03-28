import json
import logging
import os
import requests
import socket
import time

from requests.exceptions import ConnectionError
from urllib3.exceptions import NewConnectionError


class DarkSky:
    """
    Create a weather object using data from the DarkSky.net API
    :param location: optional string of coordinates for a location to fetch weather for

    properties:
    current: show current weather
    hourly: show hourly weather for the rest of the day
    daily: show daily weather for the next week

    methods:
    """
    def __init__(self, coordinates=None):
        self.coordinates = coordinates
        self._api_key = os.environ.get('DARKSKY_API_KEY')
        self._base_url = f"https://api.darksky.net/forecast/{self._api_key}/"
        self.all_weather = self.get_all_weather()
        self.current_weather = self.get_current_weather()

    @classmethod
    def fetch_weather(cls, coordinates):
        return cls(coordinates=coordinates)

    def _api_request(self, coordinates):
        """
        API GET request for weather from DarkSky.net
        """
        if not coordinates:
            return
        url = f"{self._base_url}{coordinates}"
        logging.info(url)
        try:
            request = requests.get(url)
        except (socket.gaierror, NewConnectionError, ConnectionError):
            logging.error('What The Fuck?')
            time.sleep(1)
            try:
                request = requests.get(url)
            except NewConnectionError:
                logging.error('New Connection Error')
                time.sleep(1)
                try:
                    request = requests.get(url)
                except requests.exceptions.ConnectionError:
                    logging.info('Connection Error')
                    time.sleep(1)
                    request = requests.get(url)
        logging.info(request.status_code)
        if request.status_code == 200:
            return request.json()

    def get_all_weather(self):
        logging.info(f"Coordinates: {self.coordinates}")
        data = self._api_request(self.coordinates)
        return data

    def get_current_weather(self):
        if self.all_weather:
            return self.all_weather.get('currently')
        else:
            logging.info('NO Weather')


def main():
    shit = DarkSky()
    sp = shit.fetch_weather('27.778853,-82.654820')
    print(json.dumps(sp.current_weather, indent=2))

if __name__ == '__main__':
    main()
