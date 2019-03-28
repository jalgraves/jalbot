import json
import os

from unittest import TestCase
from unittest.mock import patch, Mock
#from utils.ArgParser import parse_args, parse_option
#from utils.GetConfig import get_config
from commands import example


class TestExample(TestCase):
    @patch('commands.example.BotCommand')
    def test_example(self, MockEx):
        test_ex = MockEx()

        test_ex.ex_test5.return_value = "Example test string"
        response = test_ex.ex_test5()
        #self.assertIsNotNone(response)
        self.assertEqual(response, "Example test string", "not the same")

    def tearDown(self):
        pass
