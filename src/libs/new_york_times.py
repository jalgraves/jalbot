import logging
import requests
import socket

from urllib3 import exceptions


class NYTimesError(Exception):
    """Base class for NYTTimes exceptions"""
    pass


class NYTimes:
    """
    Create news article object from the New York Times API
    """
    def __init__(self, api_key):
        self.session = requests.session()
        self.key = api_key

    def _nyt_request(self, url):
        """
        GET request to NYT API
        """
        headers = {"api-key": self.key}
        try:
            request = self.session.get(url, headers=headers)
        except socket.gaierror as err:
            print("SOCKET ERROR")
            print(err.__class__.__name__)
        except exceptions.NewConnectionError as err:
            print('NEW CONNECTION ERROR')
        except ConnectionError as err:
            print('CONNECTION ERROR')
        print(request.status_code)
        if request.status_code != 200:
            logging.error(f"Error with NYT API request | status: {request.status_code}\n{request.content}")
            data = None
        else:
            data = request.json()
        return data

    def get_articles(self, news_subject=None):
        """
        Get articles
        """
        if not news_subject:
            url = 'https://api.nytimes.com/svc/topstories/v2/home.json'
        else:
            url = f'https://api.nytimes.com/svc/topstories/v2/{news_subject}.json'
        data = self._nyt_request(url)
        if data:
            articles = data['results']
        else:
            articles = data
        return articles


def print_articles(subject, num_articles, articles):
    """
    Print articles
    """
    article_list = [f"\n{subject.capitalize()} Articles\n"]
    for i in range(0, int(num_articles)):
        article_list.append(f"{articles[i]['title']}")
        article_list.append(f"{articles[i]['abstract']}")
        article_list.append(f"{articles[i]['url']}")
        article_list.append(f"{articles[i]['created_date']}")
    print("\n".join(article_list))


def main():
    """
    Main function
    """
    api_key = 'a8b1a4bdde5f48f88165b1d72f3d75ab'
    news = NYTimes(api_key)
    tech = news.tech_news
    headlines = news.top_news
    science = news.sciecnce_news
    sports = news.sports_news
    print_articles("Headlines", 5, headlines)
    print_articles("Science", 5, science)
    print_articles("Tech", 5, tech)
    print_articles("Sports", 5, sports)


if __name__ == '__main__':
    main()
