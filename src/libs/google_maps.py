import logging
import os
import requests
import socket
import time

from urllib3.exceptions import NewConnectionError


class GoogleMaps:
    """
    Find the coordinates of a location
    """
    def __init__(self, location):
        self.location = location
        logging.info(self.location)

    def _api_request(self):
        api_key = os.environ.get('GOOGLE_API_KEY')
        url = 'https://maps.googleapis.com/maps/api/place/findplacefromtext/json?'
        params = {
            'input': self.location,
            'inputtype': 'textquery',
            'fields': 'geometry/location',
            'key': api_key
        }
        try:
            request = requests.get(url, params=params, verify=False)
        except socket.gaierror:
            logging.error('SOCKET GAIERROR')
            time.sleep(1)
            try:
                request = requests.get(url, params=params, verify=False)
            except NewConnectionError:
                logging.error('New Connection Error')
                time.sleep(1)
                try:
                    request = requests.get(url, params=params, verify=False)
                except requests.exceptions.ConnectionError:
                    logging.info('Connection Error')
                    time.sleep(1)
                    request = requests.get(url, params=params, verify=False)
        logging.info(request.status_code)
        if request.status_code == 200:
            return request.json()

    @property
    def coordinates(self):
        data = self._api_request()
        if data:
            logging.info(data)
            candidates = data['candidates']
            if len(candidates) == 1:
                coordinates = candidates[0]['geometry']['location']
                location = f"{coordinates['lat']},{coordinates['lng']}"
                return location


def main():
    location = GoogleMaps('Boston MA').coordinates
    print(location)


if __name__ == '__main__':
    main()
