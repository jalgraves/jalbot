
import datetime
import json  # noqa
import logging  # noqa

from libs.google_maps import GoogleMaps
from libs.darksky import DarkSky
from utils.exceptions import JalBotError
from utils.BotTools import get_config
from utils.slackparse import SlackArgParse


class BotCommand(object):
    """Create Geo object from Slack event"""
    def __init__(self, event, user):
        self.text = event['text']
        self.config = get_config('weather.json')
        self.parsed_args = SlackArgParse(self.config['valid_args'], self.config['options'], event['text'])
        self.args = self.parsed_args.args
        self.option = self.parsed_args.option
        self.response = self.run_cmd()

    @property
    def location(self):
        """
        Get location from bot args
        """
        location = self.args.get('location')
        if not location:
            raise JalBotError('Missing required argument -l|-location')
        return location

    @property
    def coordinates(self):
        """
        Get coordinates of location from Google Maps API
        """
        location = GoogleMaps(self.location)
        coordinates = location.coordinates
        return coordinates

    def run_cmd(self):
        if self.text.split()[1] == 'help':
            response = "\n".join(self.config['help'])
        else:
            weather_command = {
                'current': self.current_weather,
                'forecast': self.forecast_weather,
            }
            command = weather_command.get(self.option)
            response = command()
        return response

    def current_weather(self):
        """
        Build Slack formatted message with current weather
        """
        weather = DarkSky(self.coordinates)
        current_weather = weather.current_weather
        reply = [f"*Current Weather in {self.format_location(self.location)}*"]
        summary = current_weather['summary']
        temp = current_weather['temperature']
        feels_like = current_weather['apparentTemperature']
        rain_chance = current_weather['precipProbability']
        wind_speed = current_weather['windSpeed']
        cloud_cover = current_weather['cloudCover']
        icon = current_weather['icon']
        emoji = self.get_emoji(icon)
        logging.info(f"Weather Icon: {icon}")
        weather_message = [
            f"{emoji} *{summary}*",
            f">*Temperature: `{temp}`*",
            f">*Feels Like: `{feels_like}`*",
            f">*Chance of Rain: `{rain_chance}`*",
            f">*Wind Speed: `{wind_speed}`*",
            f">*Cloud Cover: `{cloud_cover}`*"
        ]
        reply.append("\n".join(weather_message))
        return "\n".join(reply)

    def forecast_weather(self):
        """
        Build Slack formatted message with forecasted weather
        """
        pass

    def get_emoji(self, icon):
        """
        Map the DarkSky API weather icon to a Slack emoji
        """
        emojis = self.config['emojis']
        emoji = emojis.get(icon, '')
        return emoji

    @staticmethod
    def format_location(location):
        """
        Format visual representation of location for Slack
        """
        local = location.split()
        if len(local) > 1:
            if len(local) == 2 and len(local[1]) == 2:
                location = f"{local[0].title()} {local[1].upper()}"
            elif len(local) == 3 and len(local[2]) == 2:
                location = f"{local[0].title()} {local[1].title()} {local[2].upper()}"
            else:
                location = location.title()
        else:
            location = local[0].title()
        return location
