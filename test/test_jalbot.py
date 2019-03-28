import os
import json
import jalbot

from unittest import TestCase
from unittest.mock import patch
#from libs import slack
from utils.BotTools import get_config


class TestJalBot(TestCase):
    def setUp(self):
        with open('/jalbot/config/testdata/event.json', 'r') as f:
            self.config = json.load(f)

    def tearDown(self):
        pass
