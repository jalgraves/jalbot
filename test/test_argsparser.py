from unittest import TestCase

from utils.slackparse import SlackArgParse
from utils.BotTools import get_config


class TestArgParser(TestCase):
    def setUp(self):
        self.config = get_config('sports.json')

        self.cmd_args = self.config['valid_args']
        self.options = self.config['options']
        self.nhl_text = 'sports standings -l nhl --conference'

    def test_parse_args(self):
        parse_args = SlackArgParse(self.cmd_args, self.options, self.nhl_text)
        args = parse_args.parsed_args
        expected_args = {
            'league': 'nhl',
            'team': False,
            'games': False,
            'season': False,
            'player': False,
            'week': False,
            'category': False,
            'conference': True,
            'division': False,
            'matchup': False
        }

        for i in expected_args.keys():
            assert(args[i] == expected_args[i])

    def test_parse_option(self):
        parse_args = SlackArgParse(self.cmd_args, self.options, self.nhl_text)
        args = parse_args.parsed_args
        option = args.parsed_args.option
        assert(option == 'standings')

    def tearDown(self):
        pass
