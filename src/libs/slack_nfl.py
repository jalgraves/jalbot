import datetime
import logging

from libs.nfl import NFL
from libs.nfl import NFLTeam
from libs.nfl_scrape import NFLScrape
from utils.BotTools import get_config
# from utils.Exceptions import NFLException


class SlackNFL:
    """
    Create a Slack response object`
    """
    def __init__(self, args, option, team=None, player=None):
        self.args = args
        self.option = option
        self.team = team
        self.player = player
        self.config = get_config('nfl_config.json')
        self.emojis = self.config['emojis']
        self.nfl = NFL()

    @property
    def reply(self):
        logging.info(self.args)
        """
        Return Slack formatted message reply
        """
        options = {
            'scores': self.nfl_scores_reply,
            'schedule': self.nfl_schedule_reply,
            'stats': self.nfl_stats_reply,
            'standings': self.nfl_standings_reply,
            'matchup': self.nfl_matchup
        }
        option = options.get(self.option)
        response = option()
        return response

    def nfl_stats_reply(self):
        if not self.player:
            return self.nfl_team_stats()

    def nfl_schedule_reply(self):
        """
        Return Slack formatted message reply for an NFL schedule
        """
        if not self.team:
            reply = self.nfl_league_schedule()
        else:
            reply = self.nfl_team_schedule()
        return reply

    def nfl_scores_reply(self):
        """
        Build Slack reply for NFL scores
        """
        if self.team:
            reply = self.nfl_team_scores()
        else:
            reply = self.nfl_league_scores()
        return reply

    def nfl_standings_reply(self):
        division = self.args.get('division')
        conference = self.args.get('conference')
        if not division and not conference:
            reply = self.nfl_league_standings()
        elif division:
            reply = self.nfl_division_standings()
        else:
            reply = self.nfl_conference_standings()
        return reply

    def nfl_division_standings(self):
        standings = self.nfl.standings['division']
        records = self.nfl.standings['records']
        reply = [f":nfl: *Division Standings*"]
        for division, teams in standings.items():
            if division.startswith('AFC'):
                div_emoji = 'afc'
            else:
                div_emoji = 'nfc'
            standings = [f":{div_emoji}: *{division.split()[1]}*"]
            sorted_teams = sorted(teams.items(), key=lambda k: int(k[1]))
            for team in sorted_teams:
                name, rank = team
                emoji = self.emojis.get(name.lower())
                record = records.get(name)
                if len(str(rank)) == 1:
                    standings.append(f">*{rank}   :{emoji}:  {name} `{self.stringify_record(record)}`*")
                else:
                    standings.append(f">*{rank} :{emoji}:  {name} `{self.stringify_record(record)}`*")
            reply.append("\n".join(standings))
        return "\n".join(reply)

    def nfl_conference_standings(self):
        """
        Build and return Slack formatted reply for nfl conference standings
        """
        conference_standings = self.nfl.standings['conference']
        records = self.nfl.standings['records']
        reply = [f":nfl: *Conference Standings*"]
        for conference, teams in conference_standings.items():
            if conference == 'AFC':
                conf_emoji = 'afc'
            else:
                conf_emoji = 'nfc'
            standings = [f":{conf_emoji}: *{conference}*"]
            sorted_teams = sorted(teams.items(), key=lambda k: int(k[1]))
            for team in sorted_teams:
                name, rank = team
                emoji = self.emojis.get(name.lower())
                record = records.get(name)
                if len(str(rank)) == 1:
                    standings.append(f">*{rank}   :{emoji}:  {name} `{self.stringify_record(record)}`*")
                else:
                    standings.append(f">*{rank} :{emoji}:  {name} `{self.stringify_record(record)}`*")
            reply.append("\n".join(standings))
        return "\n".join(reply)

    def nfl_league_standings(self):
        standings = self.nfl.standings['league']
        records = self.nfl.standings['records']
        reply = [f":nfl: *Current League Standings*"]
        sorted_standings = sorted(standings.items(), key=lambda k: int(k[1]))
        for team in sorted_standings:
            name, rank = team
            emoji = self.emojis.get(name.lower())
            record = records.get(name)
            if len(str(rank)) == 1:
                reply.append(f">*{rank}   :{emoji}:  {name} `{self.stringify_record(record)}`*")
            else:
                reply.append(f">*{rank} :{emoji}:  {name} `{self.stringify_record(record)}`*")
        return "\n".join(reply)

    def nfl_league_schedule(self):
        """
        Build Slack reply for NFL schedule
        """
        nfl = NFL()
        week = self.args.get('week')
        if not week:
            week = nfl.upcoming_week
        games = nfl.get_games_by_week(week=week)
        reply = [f":nfl: *Week {week} Games*"]
        for game in games:
            away_team = f"{game['awayTeam']['City']} {game['awayTeam']['Name']}"
            home_team = f"{game['homeTeam']['City']} {game['homeTeam']['Name']}"
            away_emoji = self.emojis.get(away_team.lower())
            home_emoji = self.emojis.get(home_team.lower())
            reply.append(f">:{away_emoji}: *{away_team} at* :{home_emoji}: *{home_team}*\n")
        return "\n".join(reply)

    @property
    def nfl_ranks(self):
        team = NFLScrape(self.team)
        ranks = team.stats['ranks']
        return ranks

    def nfl_team_stats(self):
        """
        Build and return a Slack attachment message
        """
        # offense_stats = self.nfl_ranks['team']
        offense_ranks = self.nfl_ranks['offense']

        # defense_stats = self.nfl_ranks['opponent']
        defense_ranks = self.nfl_ranks['defense']
        team = NFLTeam(team=self.team)
        team_abbreviation = self.config['abbreviations'].get(self.team)
        full_team = self.config['full_names'].get(team_abbreviation)
        emoji = self.emojis.get(self.team.lower())

        offensive_yards = [
            f"• *Plays: `{team.offense_plays}`*",
            f"• *Total: `{team.total_yards_gained}` _({self._format_number(offense_ranks['total_yards'])})_*",
            f"• *Yards Per Play: `{team.yards_per_play}`*",
            f"• *Yards Per Game: `{team.offense_yards_per_game}`*\n"
        ]

        defensive_yards = [
            f"• *Plays: `{team.defense_plays}`*",
            f"• *Total: `{team.total_yards_allowed}` _({self._format_number(defense_ranks['total_yards'])})_*",
            f"• *Yards Per Play: `{team.defense_yards_per_play}`*",
            f"• *Yards Per Game: `{team.defense_yards_per_game}`*\n"
        ]

        passing_yards = [
            f"• *Attempts: `{team.pass_attempts}` _({self._format_number(offense_ranks['pass_att'])})_*",
            f"• *Completions: `{team.pass_completions}`*",
            f"• *Yards: `{team.pass_yards}` _({self._format_number(offense_ranks['pass_yds'])})_*",
            f"• *Yards Per Att: `{team.pass_yards_per_attempt}` _({self._format_number(offense_ranks['pass_net_yds_per_att'])})_*\n"  # noqa
        ]

        points = [
            f"• *Scored: `{team.points_for}` _({self._format_number(offense_ranks['points'])})_*",
            f"• *Allowed: `{team.points_against}` _({self._format_number(defense_ranks['points'])})_*",
            f"• *Diff: `{team.points_diff}`*\n"
        ]

        turnovers = [
            f"• *Turnovers: `{team.turnovers}`*",
            f"• *Takeaways: `{team.takeaways}`*",
            f"• *Diff: `{team.turnover_diff}`*\n",
        ]

        third_down = [
            f"• *Attempts: `{team.third_down_attempts}`*",
            f"• *Conversions: `{team.third_downs}`*",
            f"• *Conversion Percentage: `{team.third_down_percentage}`*\n"
        ]

        first_down = [
            f"• *Total: `{team.first_down_total}` _({self._format_number(offense_ranks['first_down'])})_*",
            f"• *Pass: `{team.first_down_pass}`*",
            f"• *Rush: `{team.first_down_rush}`*\n"
        ]

        penalties = [
            f"• *Total: `{team.penalties}`*",
            f"• *Penalty Yards: `{team.penalty_yards}`*\n"
        ]

        sacks = [
            f"• *Allowed: `{team.offense_sacks}`*",
            f"• *Defensive: `{team.defense_sacks}`*\n"
        ]

        rushing_yards = [
            f"• *Attempts: `{team.rush_attempts}` _({self._format_number(offense_ranks['rush_att'])})_*",
            f"• *Yards: `{team.rush_yards}` _({self._format_number(offense_ranks['rush_yds'])})_*",
            f"• *Yards Per Rush: `{team.rush_average}` _({self._format_number(offense_ranks['rush_yds_per_att'])})_*\n"
        ]

        stats = {
            "fallback": f"{full_team} Stats",
            "color": "#002244",
            "title": f"{full_team}",
            "title_link": f"https://{self.team}.com/",
            "text": f":{emoji}: *{team.season} Stats*",
            "fields": [
                {
                    "title": "Record",
                    "value": f"{self.nfl_home_road_record(team)}",
                    "short": True
                },
                {
                    "title": "Turnovers",
                    "value": "\n".join(turnovers),
                    "short": True
                },
                {
                    "title": "Defensive Yards",
                    "value": "\n".join(defensive_yards),
                    "short": True
                },
                {
                    "title": "Offensive Yards",
                    "value": "\n".join(offensive_yards),
                    "short": True
                },
                {
                    "title": "Points",
                    "value": "\n".join(points),
                    "short": True
                },
                {
                    "title": "Penalties",
                    "value": "\n".join(penalties),
                    "short": True
                },
                {
                    "title": "Passing Yards",
                    "value": "\n".join(passing_yards),
                    "short": True
                },
                {
                    "title": "Rushing Yards",
                    "value": "\n".join(rushing_yards),
                    "short": True
                },
                {
                    "title": "3rd Down",
                    "value": "\n".join(third_down),
                    "short": True
                },
                {
                    "title": "1st Down",
                    "value": "\n".join(first_down),
                    "short": True
                },
                {
                    "title": "Points Scored By Quarter",
                    "value": f"{self.nfl_points_scored_by_quarter(team)}",
                    "short": True
                },
                {
                    "title": "Points Allowed By Quarter",
                    "value": f"{self.nfl_points_allowed_by_quarter(team)}",
                    "short": True
                },
                {
                    "title": "1st Down",
                    "value": "\n".join(first_down),
                    "short": True
                },
                {
                    "title": "Sacks",
                    "value": "\n".join(sacks),
                    "short": True
                }
            ],
            # "image_url": "http://my-website.com/path/to/image.jpg",
            # "thumb_url": "http://example.com/path/to/thumb.png",
            "footer": "Jalbot",
            "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
            "ts": int(datetime.datetime.now().timestamp())
        }
        return stats

    def nfl_points_scored_by_quarter(self, team, title=False):
        """
        Build Slack formatted message containing the total points scored and the
        total points allowed in each quarter for a given team
        """
        if title:
            reply = [f"*Total Points Scored by Quarter*"]
        else:
            reply = []
        points_for = [
            f"• *First: `{team.first_quarter_points_scored}`*",
            f"• *Second: `{team.second_quarter_points_scored}`*",
            f"• *Third: `{team.third_quarter_points_scored}`*",
            f"• *Fourth: `{team.fourth_quarter_points_scored}`*"
        ]
        reply.append("\n".join(points_for))
        return "\n".join(reply)

    def nfl_points_allowed_by_quarter(self, team, title=False):
        if title:
            reply = [f"*Total Points Allowed by Quarter*"]
        else:
            reply = []
        points_against = [
            f"• *First: `{team.first_quarter_points_allowed}`*",
            f"• *Second: `{team.second_quarter_points_allowed}`*",
            f"• *Third: `{team.third_quarter_points_allowed}`*",
            f"• *Fourth: `{team.fourth_quarter_points_allowed}`*"
        ]
        reply.append("\n".join(points_against))
        return "\n".join(reply)

    def nfl_home_road_record(self, team):
        """
        Build Slack formatted message containing team's home and road records
        """
        reply = [
            f"• *Home: `{team.home_record}`*",
            f"• *Road: `{team.road_record}`*"
        ]
        return "\n".join(reply)

    def nfl_matchup(self):
        """
        Return a Slack message with stats comparing two teams
        """
        matchup = self.args.get('matchup')
        team1_name, team2_name = matchup
        team1 = NFLTeam(team=team1_name)
        logging.info(dir(team1))
        team2 = NFLTeam(team=team2_name)
        team1_emoji = self.emojis.get(team1_name.lower())
        team2_emoji = self.emojis.get(team2_name.lower())
        points = [
            f"*Points Scored/Allowed/Diff*\n:{team1_emoji}:",
            f"*`{team1.points_for}`/`{team1.points_against}`/`{team1.points_diff}`*",
            f":{team2_emoji}: *`{team2.points_for}`/`{team2.points_against}`/`{team2.points_diff}`*\n"
        ]

        offense = [
            f"*Off Yards Total/Per Play/Per Game*\n:{team1_emoji}:",
            f"*`{team1.total_yards_gained}`/`{team1.yards_per_play}`/`{team1.offense_yards_per_game}`*",
            f":{team2_emoji}: *`{team2.total_yards_gained}`/`{team2.yards_per_play}`/`{team2.offense_yards_per_game}`*\n"
        ]

        passing_yards = [
            f"*Passing Atts/Comps/Yards/Per Att*\n:{team1_emoji}:",
            f"*`{team1.pass_attempts}`/`{team1.pass_completions}`/`{team1.pass_yards}`/`{team1.pass_yards_per_attempt}`*",
            f":{team2_emoji}: *`{team2.pass_attempts}`/`{team2.pass_completions}`/`{team2.pass_yards}`/`{team2.pass_yards_per_attempt}`*\n"
        ]

        turnovers = [
            f"*Turnovers/Takeaways/Diff*\n:{team1_emoji}:",
            f"*`{team1.turnovers}`/`{team1.takeaways}`/`{team1.turnover_diff}`*",
            f":{team2_emoji}: *`{team2.turnovers}`/`{team2.takeaways}`/`{team2.turnover_diff}`*\n"
        ]

        first_down = [
            f"*1st Downs Total/Rush/Pass*\n:{team1_emoji}:",
            f"*`{team1.first_down_total}`/`{team1.first_down_rush}`/`{team1.first_down_pass}`*",
            f":{team2_emoji}: *`{team2.first_down_total}`/`{team2.first_down_rush}`/`{team2.first_down_pass}`*\n"
        ]

        game_text = [
            f"*Home Record*\n:{team1_emoji}: *`{team1.home_record}`* :{team2_emoji}: *`{team2.home_record}`*",
            f"*Road Record*\n:{team1_emoji}: *`{team1.road_record}`* :{team2_emoji}: *`{team2.road_record}`*",
            " ".join(points),
            " ".join(offense),
            " ".join(passing_yards),
            " ".join(turnovers),
            " ".join(first_down)
        ]
        match = {
            "fallback": f"{team1_name} vs. {team2_name}",
            "color": "#002244",
            "title": f"{team1_name.title()} vs {team2_name.title()}",
            "title_link": f"https://{self.team}.com/",
            "text": "\n".join(game_text),
            "fields": [

                {
                    "title": f":{team1_emoji}: Games",
                    "value": self.nfl_matchup_scores(team=team1_name, title=False),
                    "short": True
                },
                {
                    "title": f":{team2_emoji}: Games",
                    "value": self.nfl_matchup_scores(team=team2_name, title=False),
                    "short": True
                }
            ],
            "footer": "Jalbot",
            "footer_icon": ":nfl:",
            "ts": int(datetime.datetime.now().timestamp())
        }
        return match

    def nfl_team_schedule(self):
        """
        Build Slack formatted reply with an NFL team's schedule
        """
        nfl = NFLTeam(team=self.team)
        team_abbreviation = self.config['abbreviations'].get(self.team)
        full_team = self.config['full_names'].get(team_abbreviation)
        emoji = self.emojis.get(self.team.lower())
        reply = [
            f":{emoji}: *{full_team} {nfl.season} Schedule*",
            self.nfl_team_scores(title=False)
        ]

        for game in nfl.unplayed_games:
            week = game['week']
            away_team_city = game['awayTeam']['City']
            away_team = game['awayTeam']['Name']
            home_team_city = game['homeTeam']['City']
            home_team = game['homeTeam']['Name']
            away_team = self.check_city(away_team_city, away_team)
            home_team = self.check_city(home_team_city, home_team)
            away_emoji = self.emojis.get(away_team.lower())
            home_emoji = self.emojis.get(home_team.lower())
            reply.append(f"*Week {week}*\n>:{away_emoji}: *{away_team} at {home_team}* :{home_emoji}:")
        return "\n".join(reply)

    def check_city(self, city, team):
        """
        Make sure the correct team is returned for cities that have multiple teams
        """
        if city == 'New York' or city == 'Los Angeles':
            abbr = city.split()
            team_city = f"{abbr[0][0]}{abbr[1][0]}"
            team = f"{team_city} {team}"
        else:
            team = city
        return team

    def stringify_record(self, record):
        """
        Convert team record dict into string
        """
        wins = record['wins']
        losses = record['losses']
        ties = record['ties']
        record = f"{wins}-{losses}-{ties}"
        return record

    def nfl_team_scores(self, team=None, title=True):
        """
        Build Slack formatted reply containing games scores for an NFL team
        """
        if not team:
            team = self.team
        team = NFLTeam(team=team)
        team_abbreviation = self.config['abbreviations'].get(team.team.lower)
        full_team = self.config['full_names'].get(team_abbreviation)
        emoji = self.emojis.get(team.team.lower())
        played_games = sorted(team.team_game_results, key=lambda k: int(k['week']))
        if title:
            reply = [f":{emoji}: *{full_team} {team.season} Scores*"]
        else:
            reply = []
        for game in played_games:
            week = game['week']
            away_team_city = game['awayTeam']['City']
            away_team = game['awayTeam']['Name']
            home_team_city = game['homeTeam']['City']
            home_team = game['homeTeam']['Name']
            away_team_score = game['game_score']['awayScore']
            home_team_score = game['game_score']['homeScore']
            away_team = self.check_city(away_team_city, away_team)
            home_team = self.check_city(home_team_city, home_team)
            away_emoji = self.emojis.get(away_team.lower())
            home_emoji = self.emojis.get(home_team.lower())
            game_message = [
                f"*Week {week}*",
                f">:{away_emoji}: *{away_team}: `{away_team_score}`*",
                f">:{home_emoji}: *{home_team}: `{home_team_score}`*"
            ]
            reply.append("\n".join(game_message))
        return "\n".join(reply)

    def nfl_matchup_scores(self, team=None, title=True):
        """
        Build Slack formatted reply containing games scores for an NFL team
        """
        if not team:
            team = self.team
        team = NFLTeam(team=team)
        team_abbreviation = self.config['abbreviations'].get(team.team.lower)
        full_team = self.config['full_names'].get(team_abbreviation)
        emoji = self.emojis.get(team.team.lower())
        played_games = sorted(team.team_game_results, key=lambda k: int(k['week']))
        if title:
            reply = [f":{emoji}: *{full_team} {team.season} Scores*"]
        else:
            reply = []
        for game in played_games:
            away_team_city = game['awayTeam']['City']
            away_team = game['awayTeam']['Name']
            home_team_city = game['homeTeam']['City']
            home_team = game['homeTeam']['Name']
            away_team_score = game['game_score']['awayScore']
            home_team_score = game['game_score']['homeScore']
            away_team = self.check_city(away_team_city, away_team)
            home_team = self.check_city(home_team_city, home_team)
            away_emoji = self.emojis.get(away_team.lower())
            home_emoji = self.emojis.get(home_team.lower())
            game_message = f":{away_emoji}: *`{away_team_score}`* *at* :{home_emoji}: *`{home_team_score}`*"
            reply.append(game_message)
        return "\n".join(reply)

    def nfl_league_scores(self, title=True):
        """
        Build Slack reply with an NFL team's schedule
        """
        nfl = NFL()
        games = nfl.league_game_results
        week = games[0]['week']
        if title:
            reply = [f":nfl: *Week {week} scores*"]
        else:
            reply = []
        for game in games:
            away_team_city = game['awayTeam']['City']
            away_team = game['awayTeam']['Name']
            home_team_city = game['homeTeam']['City']
            home_team = game['homeTeam']['Name']
            away_team_score = game['game_score']['awayScore']
            home_team_score = game['game_score']['homeScore']
            away_team = self.check_city(away_team_city, away_team)
            home_team = self.check_city(home_team_city, home_team)
            away_emoji = self.emojis.get(away_team.lower())
            home_emoji = self.emojis.get(home_team.lower())
            game_message = [
                f">:{away_emoji}: *{away_team}: `{away_team_score}`*",
                f">:{home_emoji}: *{home_team}: `{home_team_score}`*\n"
            ]
            reply.append("\n".join(game_message))
        return "\n".join(reply)

    def _format_date(self, date):
        """
        Format date from API into Month Day
        """
        if 'T' in date:
            date, game_time = date.split('T')
        game_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        day = game_date.strftime("%d")
        if day.startswith('0'):
            day = day[1:]
        formatted_date = game_date.strftime(f"%A, %B {day}")

        return formatted_date

    def _format_number(self, num):
        """
        Get suffix to append to number
        """
        num = int(num)
        if num in [1, 21, 31]:
            suffix = 'st'
        elif num in [2, 22, 32]:
            suffix = 'nd'
        elif num in [3, 23, 33]:
            suffix = 'rd'
        else:
            suffix = 'th'

        return f"{num}{suffix}"
