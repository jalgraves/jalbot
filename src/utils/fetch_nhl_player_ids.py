import redis
import requests
import socket
import sys
import time

from urllib3 import exceptions
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry


def fetch_nhl_ids():
    """
    Get the NHL player IDs for the API
    """
    start_num = int(sys.argv[1])
    end_num = int(sys.argv[2])
    session = requests.session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    base_url = 'https://statsapi.web.nhl.com/api/v1/people/'
    nhl_players = redis.StrictRedis(host='jal_redis.backend', port=6379, db=0)
    for i in range(start_num, end_num):
        if i % 100 == 0:
            print(i)
        if i % 10000 == 0:
            time.sleep(10)
        elif i % 50000 == 0:
            time.sleep(30)
        url = f"{base_url}/{i}"
        try:
            request = session.get(url)
        except socket.gaierror as err:
            print("SOCKET ERROR")
            print(err.__class__.__name__)
            time.sleep(2)
            request = session.get(url)
        except exceptions.NewConnectionError as err:
            print('NEW CONNECTION ERROR')
            time.sleep(2)
            request = session.get(url)
        except requests.exceptions.ConnectionError as err:
            print(f"CONNECTION ERROR checking ID {i}")
            time.sleep(5)
            request = session.get(url)
        if request.status_code == 200:
            data = request.json()
            player_info = data['people'][0]
            name = player_info.get('fullName')
            player_id = player_info['id']
            if name:
                print(name)
                nhl_players.set(name, player_id)


if __name__ == '__main__':
    fetch_nhl_ids()
