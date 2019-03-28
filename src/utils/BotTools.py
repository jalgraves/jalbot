import json
import logging
import os
import requests
import sys
import time

from functools import wraps
from requests.exceptions import ConnectTimeout, ConnectionError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

from utils.exceptions import JalBotError


class JalBotRequestsException(Exception):
    """Base class for JalBot API requests exceptions"""
    pass


def setup_logger():
    """
    Setup logger

    :return:
    """
    log_level = "INFO"
    logfile = 'log/jalbot.log'
    log_format = "{asctime} | {levelname} | {module}.{funcName}:{lineno} | {message}"

    formatter = logging.Formatter(log_format, style='{')
    formatter.converter = time.gmtime

    root = logging.getLogger()
    root.setLevel(log_level)

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    handler.setFormatter(formatter)

    file_handler = logging.FileHandler(logfile)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    root.addHandler(handler)
    root.addHandler(file_handler)
    logging.captureWarnings(True)


def set_timeout(timeout=None):
    """
    Set requests timeout default to 250 sec if not specified
    :return:
    """
    if not timeout:
        timeout = 250
    else:
        timeout = int(timeout)
    return timeout


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


def try_request(command, *args, **kwargs):
    """
    requests wrapper for API calls
    """
    command = command.capitalize()
    session = requests.session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[ 502, 503, 504 ])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    try:
        # request = requests.request(*args, **kwargs)
        request = session.get(*args, **kwargs)
        logging.info(f"{command} | {request.status_code}")
    except (ConnectTimeout, ConnectionError) as err:
        err_name = err.__class__.__name__
        raise JalBotRequestsException(f"{command} API Error {err_name}")
    if request.status_code not in range(200, 299):
        logging.info('%s | %s | %i' % (command, request.url, request.status_code))
        if not request.content:
            raise JalBotRequestsException(f"{command} API Error {request.status_code}")
        raise JalBotRequestsException(f"{command} API Error {request.status_code}\n{request.content}")
    if 'json' in dir(request):
        request = request.json()
    return request


def validate_user(func):
    """
    Check if Slack user is authortized to run priviledged commands
    """
    users = get_config('users.json')

    @wraps(func)
    def check_user(*args, **kwargs):
        cmd, user = args
        if user["user"]["id"] not in users["authorized_users"].keys():
            logging.info('Unauthorized user | %s | %s' % (user["user"]["name"], func.__name__))
            raise JalBotError('User not authorized to run bot command')
        logging.info('Authorized user | %s | %s' % (user["user"]["name"], func.__name__))
        reply = func(cmd, user)
        return reply
    return check_user


def log_command(func):
    """
    Logging decorator for logging bot commands and info
    """
    def log_command(*args, **kwargs):
        slack, command, event = args
        user = slack.user_info(event["user"])
        log_line = 'USER: %s | CHANNEL ID: %s | COMMAND: %s | TEXT: %s'
        command_info = log_line % (user["user"]["name"],
                                   event["channel"],
                                   command,
                                   event["text"])
        logging.info(command_info)
        command = func(*args, **kwargs)
        return command
    return log_command
