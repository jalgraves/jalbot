import datetime
import os

from libs.new_york_times import NYTimes
from utils.slackparse import SlackArgParse
from utils.exceptions import JalBotError
from utils.BotTools import get_config


class BotCommand:
    """Create News object from New York Times API data"""
    def __init__(self, event, user):
        self.api_key = os.environ.get('NYT_API_KEY')
        self.config = get_config('news.json')
        self.parsed_args = SlackArgParse(self.config['valid_args'], self.config['options'], event['text'])
        self.args = self.parsed_args.args
        self.option = self.parsed_args.option
        self.subject = self._get_subject()
        self.num_articles = self._get_num_articles()
        self.news = self._create_news_object()
        self.text = event['text']
        self.response = self.run_cmd()

    def run_cmd(self):
        try:
            help = self.text.split()[1]
        except IndexError:
            help = None
        if help == 'help':
            response = "\n".join(self.config['help'])
        else:
            response = self.news_response(subject=self.subject, num_articles=self.num_articles)
        return response

    def news_response(self, subject=None, num_articles=None):
        """
        Return Slack formatted response
        """
        if not num_articles:
            num_articles = 5
        if not subject:
            subject = 'Headlines'
            articles = self.news.get_articles(news_subject="home")
        else:
            articles = self.news.get_articles(news_subject=subject)
            if not articles:
                response = f"_*No articles found under `{subject}`*_"
                return response
        article_list = [f"*{subject.capitalize()}*\n"]
        for i in range(0, int(num_articles)):
            date = self._format_date(articles[i]['created_date'])
            article_list.append(f"*<{articles[i]['url']}|{articles[i]['title']}>*")
            article_list.append(f">*{date}*")
            article_list.append(f">{articles[i]['abstract']}\n")
        article_list.append(":nyt: *<http://developer.nytimes.com|Data provided by The New York Times>*")
        response = "\n".join(article_list)
        return response

    def _create_news_object(self):
        """
        Create news object from NYTimes class
        """
        try:
            news_object = NYTimes(self.api_key)
        except Exception as err: # noqa
            raise JalBotError(f"{err}")
        return news_object

    def _format_date(self, date):
        """
        Format date from API into Month Day
        """
        date, time = date.split('T')
        article_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        day = article_date.strftime("%d")
        if day.startswith('0'):
            day = day[1:]
        formatted_date = article_date.strftime(f"%A %B {day}, %Y")

        return formatted_date

    def _get_subject(self):
        """
        Get the subject from the parsed args
        """
        subject = self.args.get('subject')
        return subject

    def _get_num_articles(self):
        """
        Get the number of articles to display
        """
        num_articles = self.args.get('number')
        return num_articles
