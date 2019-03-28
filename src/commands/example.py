import logging

from utils.BotTools import get_config
from utils.slackparse import SlackArgParse
from utils.exceptions import JalBotError


class BotCommand(object):
    """Create Example object from Slack event"""
    def __init__(self, event, user):
        self.config = get_config('example.json')
        self.parsed_args = SlackArgParse(self.config['valid_args'], self.config['options'], event['text'])
        self.args = self.parsed_args.args
        self.option = self.parsed_args.option
        self.response = self.run_cmd()

    def run_cmd(self):
        """
        Options and arguments for a command are defined in the commands config
        json file. So the options and args for this command are defined in
        config/example.json

        This function works as the factory that generates a Slack reply based
        on the bot message that provides the options and args
        """
        logging.info("Running example bot command to retrieve reply message")
        # the keys in cmds correspond to a commands options
        cmds = {
            'hello': self.hello_world,
            'info': self.print_info
        }
        func = cmds.get(self.option, None)
        response = func()
        return response

    def hello_world(self):
        """
        This is an example reply

        The Slack message 'jalbot example hello' would trigger this function
        and reply
        """
        # add code here to create custom response
        # for example get the input from the custom args that are definded in
        # config/example.json and use them to build a custom reply
        name = self.args.get('name')
        if name:
            reply = f"Hello world, I'm {name}"
        else:
            reply = "Hello world"
        return reply

    def print_info(self):
        """
        Get the name and age from the parsed command args and return them in
        Slack reply

        The Slack message 'jalbot example info -name joe somebody -age 100'
        would trigger this function and reply
        If either the -name <name> or -age <age> were missing an error reply
        would be sent
        """
        name = self.args.get('name')
        age = self.args.get('age')
        if not name:
            # this will return an Error reply to Slack if an argument for the
            # function to work is missing
            raise JalBotError('Missing required arg -n <name> or -name <name>')
        if not age:
            raise JalBotError('Missing required arg - <name> or -age <age>')
        reply = f"My name is {name} and I'm {age} years old"
        return reply


if __name__ == '__main__':
    print('Running main')
