import datetime
import logging
import json

# from libs.nba import NBATeam
from libs.nba import NBALeague
from utils.BotTools import get_config
from utils.exceptions import NBAException


class SlackNBA:
    """
    Create a Slack response object`
    """
    def __init__(self, args, option, team=None, player=None):
        self.args = args
        self.option = option
        self.team = team
        self.player = player
        self.config = get_config('nba.json')

    @property
    def reply(self):
        """
        Return Slack formatted message reply
        """
        options = {
            'scores': self.nba_scores_reply,
            'schedule': self.nba_schedule_reply,
            # 'stats': self.nba_stats_reply,
            # 'roster': self.nba_roster,
            # 'career': self.nba_career_stats,
            'standings': self.nba_standings_reply
        }
        option = options.get(self.option)
        response = option()
        return response

    def nba_scores_reply(self):
        if not self.team:
            reply = self.nba_league_scores()
        else:
            reply = self.nba_team_scores()
        return reply

    def nba_schedule_reply(self):
        if not self.team:
            reply = self.nba_league_schedule()
        else:
            reply = self.nba_team_schedule()
        return reply

    def nba_standings_reply(self):
        conference = self.args.get('conference')
        division = self.args.get('division')
        if not conference and not division:
            reply = self.nba_league_standings()
        elif conference:
            reply = self.nba_conference_standings()
        return reply

    def nba_stats_reply(self):
        if not self.team and not self.player:
            err_message = [
                'Missing player or team to retrieve stats for'
                'For team stats run command like this for example',
                'jalbot sports stats -l nba -t boston',
                'Or for player stats run like this',
                'jalbot sports stats -l nba -p kyrie irving'
            ]
            raise NBAException("\n".join(err_message))
        if self.team:
            reply = self.nba_team_stats()
        elif self.player:
            reply = self.nba_player_stats()
        return reply

    def nba_league_standings(self):
        """
        Buil Slack formatted reply with NBA overall standings
        """
        nba = NBALeague()
        standings = nba.overall_standings
        logging.info(standings)
        # sorted_teams = sorted(teams.items(), key=lambda k: int(k[1]))
        reply = [f":nba: *2018-19 Overall Standings*"]
        for k, v in standings.items():
            logging.info(f"{k} {v}")
            team_name = self.config['ids'].get(k)
            team_emoji = self.get_emoji(team_name)
            record = nba.record(k)
            reply.append(f">:{team_emoji}: *{team_name.title()} `{record}`*")
        return "\n".join(reply)

    def nba_conference_standings(self):
        """
        Buil Slack formatted reply with NBA overall standings
        """
        nba = NBALeague()
        east = nba.eastern_conference_standings
        west = nba.western_conference_standings
        reply = [f":nba: *2018-19 Conference Standings*"]
        east_conf = [":nba_east: *Eastern*"]
        west_conf = [":nba_west: *Western*"]
        for k, v in east.items():
            team_name = self.config['ids'].get(k)
            team_emoji = self.get_emoji(team_name)
            record = nba.record(k)
            east_conf.append(f">:{team_emoji}: *{team_name.title()} `{record}`*")
        reply.append("\n".join(east_conf))
        for k, v in west.items():
            team_name = self.config['ids'].get(k)
            team_emoji = self.get_emoji(team_name)
            record = nba.record(k)
            west_conf.append(f">:{team_emoji}: *{team_name.title()} `{record}`*")
        reply.append("\n".join(west_conf))
        return "\n".join(reply)

    def nba_league_schedule(self, title=True, limit=None, type=None):
        """Format slack reply"""
        nba = NBALeague()
        games = nba.todays_games
        if not title:
            reply = []
        else:
            reply = [f":nba: *Today's Games*"]
        if games.unplayed:
            for game in games.unplayed:
                away_team = game['away_team']
                away_record = game['away_record']
                home_team = game['home_team']
                home_record = game['home_record']
                away_emoji = self.get_emoji(away_team)
                home_emoji = self.get_emoji(home_team)
                game_message = [
                    f"*{game['game_time']}*",
                    f">*:{away_emoji}: {away_team.title()} `{away_record}`* ",
                    f">*:{home_emoji}: {home_team.title()} `{home_record}`*"
                ]
                reply.append("\n".join(game_message))
        elif games.live:
            for game in games.live:
                away_team = game['away_team']
                home_team = game['home_team']
                away_emoji = self.get_emoji(away_team)
                home_emoji = self.get_emoji(home_team)
                home_score = game['home_team_score']
                away_score = game['away_team_score']
                game_message = [
                    f"*{game['game_time']}*",
                    f">*:{away_emoji}: {away_team.title()} `{away_score}`* ",
                    f">*:{home_emoji}: {home_team.title()} `{home_score}`*"
                ]
                reply.append("\n".join(game_message))
        elif games.final:
            for game in games.final:
                away_team = game['away_team']
                home_team = game['home_team']
                away_emoji = self.get_emoji(away_team)
                home_emoji = self.get_emoji(home_team)
                home_score = game['home_team_score']
                away_score = game['away_team_score']
                game_message = [
                    f"*{game['game_time']}*",
                    f">*:{away_emoji}: {away_team.title()} `{away_score}`* ",
                    f">*:{home_emoji}: {home_team.title()} `{home_score}`*"
                ]
                reply.append("\n".join(game_message))
        else:
            return ":nba: _*No games scheduled today*_"
        return "\n".join(reply)

    def nba_league_scores(self):
        nba = NBALeague()
        games = nba.recent_scores()
        reply = [":nba: *Recent Scores*"]
        for game in games:
            away_team = game['away_team']
            home_team = game['home_team']
            away_emoji = self.get_emoji(away_team)
            home_emoji = self.get_emoji(home_team)
            home_score = game['home_team_score']
            away_score = game['away_team_score']
            game_message = [
                f">*:{away_emoji}: {away_team.title()} `{away_score}`* ",
                f">*:{home_emoji}: {home_team.title()} `{home_score}`*\n"
            ]
            reply.append("\n".join(game_message))
        return "\n".join(reply)

    def get_emoji(self, team):
        abbreviations = self.config['abbreviations']
        emojis = self.config['emojis']
        team_abbreviation = abbreviations.get(team)
        if not team_abbreviation:
            team_abbreviation = abbreviations.get(team.split(' ', 1)[0])
        emoji = emojis.get(team_abbreviation)
        return emoji
