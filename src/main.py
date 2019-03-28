import logging
import os
import time

from libs import slack

from utils.BotTools import setup_logger


class JalBot(object):
    """
    Create slackbot object
    """
    def __init__(self, slack_token):
        """
        Initialize JalBot

        :param slack_token: Slack API token
        """
        self.slack_token = slack_token
        self.slack = slack.Slack(self.slack_token)

    def slackbot(self, *args, **kwargs):
        """
        Run JalBot as daemon for live interaction through Slack
        """
        while True:
            self.slack.api_connect()

def main():
    """
    Main function run when called from command line

    :return:
    """
    setup_logger()
    token = os.environ.get('JAL_SLACK_TOKEN')
    jalbot = JalBot(token)
    logging.info('starting slackbot')
    try:
        output = jalbot.slackbot()
    except Exception as err:
        logging.error(f"JALBOT main() EXCEPTION\n{err}")
        time.sleep(2)
        output = jalbot.slackbot()
    if output:
        print(output)


if __name__ == '__main__':
    main()
