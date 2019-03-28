from utils.BotTools import get_config


class BotCommand(object):
    """Create help object from Slack event"""
    def __init__(self, event, user):
        self.config = get_config('help.json')
        try:
            self.option = event["text"].split()[1]
        except IndexError:
            self.option = False
        self.option = False
        self.user = event["user"]

    def run_cmd(self, *args):
        """Run help command"""
        conf = get_config('help.json')
        response = conf["help"]
        if not self.option:
            response = self.config["help"]
        else:
            get_help = get_config(f'{self.option}.json')
            response = get_help["help"]
        return "\n".join(response)
