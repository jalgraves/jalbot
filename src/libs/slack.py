import slackclient
import logging
import time
import traceback
import os
import requests
import importlib
import inspect
import sys
import asyncio

from time import sleep
from threading import Thread

from utils.BotTools import get_config, log_command
from utils.exceptions import JalBotError
from utils.exceptions import NFLRequestException
from utils.exceptions import NHLException
from utils.exceptions import NBAException

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class Slack(object):
    def __init__(self, token):
        """
        Initialize the Slack object given the provided bot token

        :param token:
        :param config:
        """
        self.config = get_config('slack.json')
        self.client = slackclient.SlackClient(token)
        self.commands = self.load_commands('/jalbot/src/commands/')

    def post_message(self, channel, message):
        """
        Post the provided message to the given channel

        :param channel:
        :param message:
        :return:
        """
        if isinstance(message, dict):
            self.client.api_call("chat.postMessage",
                                 channel=channel,
                                 attachments=[message],
                                 as_user=True)
        else:
            self.client.api_call("chat.postMessage",
                                 channel=channel,
                                 text=message,
                                 as_user=True)

    def post_reaction(self, emoji, ts, channel):
        """
        Post the provided message to the given channel

        :param channel:
        :param message:
        :return:
        """
        self.client.api_call("reactions.add",
                             name=emoji,
                             timestamp=ts,
                             channel=channel)

    def del_reaction(self, emoji, msg_id, channel):
        """
        Post the provided message to the given channel

        :param channel:
        :param message:
        :return:
        """
        self.client.api_call("reactions.remove",
                             name=emoji,
                             timestamp=msg_id,
                             channel=channel)

    def user_info(self, user_id):
        """
        Post the provided message to the given channel

        :param channel:
        :param message:
        :return:
        """
        info = self.client.api_call("users.info", user=user_id)
        return info

    def channel_info(self, channel_id):
        """
        Post the provided message to the given channel

        :param channel:
        :param message:
        :return:
        """
        info = self.client.api_call("channels.info", channel=channel_id)
        if not info["ok"]:
            info = None
        return info

    @staticmethod
    def slack_worker(loop):
        """
        Slack event loop
        """
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def api_connect(self):
        """
        Connect to Slack Real Time Messaging API
        :return:
        """
        client = self.client.rtm_connect()
        if client:
            logging.info('Connected to Slack')
            worker_loop = asyncio.new_event_loop()
            worker = Thread(target=self.slack_worker, args=(worker_loop, ))
            worker.start()
            while True:
                try:
                    events = self.client.rtm_read()
                except Exception as err:
                    time.sleep(1)
                    events = self.client.rtm_read()
                for event in events:
                    try:
                        if event.get('text'):
                            bot_text = self.get_bot_command(event["text"])
                            if bot_text:
                                event["text"] = bot_text[1]
                                command = bot_text[0]
                                self.post_reaction("spinning", event["ts"], event["channel"])
                                worker_loop.run_in_executor(None, self.handle_message, command, event)
                    except requests.exceptions.ConnectionError as err:
                        logging.error(err)
                        sleep(2)
                        self.client.rtm_connect()
                        self.post_reaction("spinning", event["ts"], event["channel"])
                        worker_loop.run_in_executor(None, self.handle_message, command, event)

    @staticmethod
    def load_commands(command_path):
        """
        Load commands
        """
        logging.info("Loading bot commands")
        sys.path.append(command_path)

        commands = {}
        for command in os.listdir(command_path):
            if not command.startswith('_'):
                cmd = importlib.import_module(command[:-3])
                cmd_funcs = dict(inspect.getmembers(cmd, inspect.isclass))
                cmd_func = cmd_funcs.get('BotCommand')
                cmd_name = repr(cmd_func).strip('<class ').strip('>')
                logging.info('LOADING %s' % (cmd_name))
                commands[command[:-3]] = cmd_func
        return commands

    def get_bot_command(self, text=None):
        """
        Check if Slack message is a command for JalBot
        :param text:
        :return:
        """
        if not text:
            return
        # names bot will respond to
        bot = text.split(None, 1)[0].lower().strip()
        if bot not in self.config["bot_names"]:
            return
        bot_text = text.split(None, 1)[1].strip().replace('  ', ' ')
        bot_command = bot_text.split()[0]
        return (bot_command, bot_text)

    def post_to_slack(self, response, event, emoji):
        """
        Post reply to Slack and add command complete emoji
        """
        self.post_message(event["channel"], response)
        self.del_reaction("spinning", event["ts"], event["channel"])
        self.post_reaction(emoji, event["ts"], event["channel"])
        return

    def get_func(self, command, event):
        """
        Return the correct module for the requested command
        """
        if command in self.config["commands"]["alt_names"].keys():
            command = self.config["commands"]["alt_names"][command]
        func = self.commands.get(command)
        if not func:
            response = f':red_dot: _*JalBot Error*_```Unknown Command: {command}```'
            self.post_to_slack(response, event, 'x')
            return
        return func

    @log_command
    def handle_message(self, command, event):
        """
        Handle Slack messages sent to JalBot
        :param event:
        """
        user = self.user_info(event["user"])
        func = self.get_func(command, event)
        try:
            bot_command = func(event, user)
            response = bot_command.run_cmd()
        except JalBotError as err:
            response = f":red_dot: _*JalBot {command.upper()} Error*_```{err}```"
            self.post_to_slack(response, event, 'x')
            return
        except NFLRequestException as err:
            response = f":nfl: _*NFL Error*_```{err}```"
            self.post_to_slack(response, event, 'x')
            return
        except NHLException as err:
            response = f":nhl: _*NHL Error*_```{err}```"
            self.post_to_slack(response, event, 'x')
            return
        except NBAException as err:
            response = f":nba: _*NBA Error*_```{err}```"
            self.post_to_slack(response, event, 'x')
            return
        except Exception as err:
            logging.error(f'JalBot exception | {err}\n{traceback.format_exc()}')
            response = [
                f':red_dot: _*JalBot Exception*_',
                f'```{traceback.format_exc(limit=2)}```',
                f'_*See logs for further details*_'
            ]
            self.post_to_slack("\n".join(response), event, 'skull_and_crossbones')
            return
        try:
            self.post_to_slack(response, event, 'robot_face')
        except Exception as err:
            logging.error(f'ERROR POSTING TO SLACK API: {err}')
            time.sleep(1)
            self.client.rtm_connect()
            self.post_message(event["channel"], response)
