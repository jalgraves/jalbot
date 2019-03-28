import datetime
import logging
import redis

from libs.nhl import NHL
from libs.nhl import NHLTeam
from libs.nhl import NHLLeague
from libs.nhl import NHLPlayer
from utils.BotTools import get_config
from utils.exceptions import NHLException


class SlackNHL:
    """
    Create a Slack response object`
    """
    def __init__(self, args, option, team=None, player=None):
        self.args = args
        self.option = option
        self.team = team
        self.player = player
        self.config = get_config('nhl_config.json')
        self.emojis = self.config['emojis']
        self.nhl = NHL()

    @property
    def reply(self):
        logging.info(self.args)
        """
        Return Slack formatted message reply
        """
        options = {
            'scores': self.nhl_scores_reply,
            'schedule': self.nhl_schedule_reply,
            'stats': self.nhl_stats_reply,
            'roster': self.nhl_roster,
            'career': self.nhl_career_stats,
            'standings': self.nhl_standings
        }
        option = options.get(self.option)
        response = option()
        return response

    def nhl_scores_reply(self):
        if not self.team:
            reply = self.nhl_league_scores()
        else:
            reply = self.nhl_team_scores()
        return reply

    def nhl_schedule_reply(self):
        if not self.team:
            reply = self.nhl_league_schedule()
        else:
            reply = self.nhl_schedule()
        return reply

    def nhl_stats_reply(self):
        if not self.team and not self.player:
            err_message = [
                'Missing player or team to retrieve stats for:',
                'To get NHL team stats run command like this for example',
                'jalbot sports stats -l nhl -t boston',
                'Or for player stats run like this',
                'jalbot sports stats -l nhl -p brad marchand'
            ]
            raise NHLException("\n".join(err_message))
        if self.team:
            reply = self.nhl_team_stats()
        elif self.player:
            reply = self.nhl_player_stats()
        return reply

    def nhl_team_stats(self):
        """
        Return slack reply with NHL stats
        """
        team = NHLTeam(self.team)
        emoji = self.emojis.get(str(team.team))
        team_stats = team.stats
        stats = team_stats['teamStats'][0]['splits'][0]['stat']
        ranks = team_stats['teamStats'][0]['splits'][1]['stat']
        wins = stats['wins']
        losses = stats['losses']
        ot = stats['ot']
        points = stats['pts']
        last_three_games = self.nhl_team_scores(title=False, limit=3)
        next_three_games = self.nhl_schedule(title=False, limit=3, type='unplayed')
        reply = [
            f":{emoji}: *{team_stats['name']}*",
            f">*Venue: `{team.venue}`*",
            f">*Record: `{wins} - {losses} - {ot}`*",
            f">*Points: `{points}`*",
            f"*League Ranks*",
            f">*Wins: `{ranks['wins']}`*",
            f">*Goals Per Game: `{stats['goalsPerGame']} - {ranks['goalsPerGame']}`*",
            f">*Goals Against Per Game: `{stats['goalsAgainstPerGame']} - {ranks['goalsAgainstPerGame']}`*",
            f">*Power Plays: `{stats['powerPlayOpportunities']} - {ranks['powerPlayOpportunities']}`*",
            f">*Power Play Percentage: `{stats['powerPlayPercentage']} - {ranks['powerPlayPercentage']}`*",
            f">*Penalty Kill Percentage: `{stats['penaltyKillPercentage']}% - {ranks['penaltyKillPercentage']}`*",
            f"*Last 3 Games*\n{last_three_games}",
            f"*Next 3 Games*\n{next_three_games}"
        ]
        return "\n".join(reply)

    def nhl_player_stats(self):
        """
        Get player stats
        """
        season = self.args.get('season')
        if season:
            stats = self.team.get_player_season_stats(self.player, season=season)
        else:
            stats = self.team.get_player_season_stats(self.player)
        emoji = self.config['emojis'].get(str(stats['team']))
        reply = [
            f":{emoji}: *{self.player}*",
            f">*Games: `{stats['stat']['games']}`*",
            f">*Time on Ice: `{stats['stat']['timeOnIce']}`*",
            f">*Goals: `{stats['stat']['goals']}`*",
            f">*Assists: `{stats['stat']['assists']}`*",
            f">*Points: `{stats['stat']['points']}`*",
            f">*Penalty Mins: `{stats['stat']['pim']}`*",
            f">*Plus/Minus: `{stats['stat']['plusMinus']}`*",
            f">*Shifts: `{stats['stat']['shifts']}`*"
        ]
        return "\n".join(reply)

    def nhl_career_stats(self):
        """
        Get player stats
        """
        if not self.player:
            raise NHLException('Missing required arg -p|-player')
        player = NHLPlayer(self.player)
        season_stats_list = player.career_stats
        reply = [f"*{self.player}*"]
        for i in range(len(season_stats_list)):
            season = f"{season_stats_list[i]['season'][:4]} - {season_stats_list[i]['season'][4:]}"
            logging.info(season)
            stats = season_stats_list[i]['stat']
            team = season_stats_list[i]['team']['name']
            league = season_stats_list[i]['league']['name']
            games = stats.get('games', 'None')
            goals = stats.get('goals', 'None')
            assists = stats.get('assists', 'None')
            points = stats.get('points', 'None')
            season_info = [
                f"*Season {season}*",
                f">*Team: `{team}`*",
                f">*League: `{league}`*",
                f">*Games: `{games}`*",
                f">*Goals: `{goals}`*",
                f">*Assists: `{assists}`*",
                f">*Points: `{points}`*"
            ]
            reply.append("\n".join(season_info))
        return "\n".join(reply)

    def nhl_roster(self):
        """
        Return slack reply with NHL stats
        """
        team = NHLTeam(self.team)
        nhl_players = redis.StrictRedis(host='jal_redis.backend', port=6379, db=0)
        emoji = self.emojis.get(str(self.team))
        roster = team.roster
        team_stats = team.stats
        reply = [f":{emoji}: *{team_stats['name']} Roster*"]
        for i in range(len(roster)):
            player = roster[i]['person']
            nhl_players.set(player['fullName'], player['id'])
            player_info = [
                f"*{player['fullName']} {roster[i]['jerseyNumber']}*",
                f">*Position: `{roster[i]['position']['name']}`*"
            ]
            reply.append("\n".join(player_info))
        return "\n".join(reply)

    def nhl_schedule(self, title=True, limit=None, type=None):
        """Format slack reply"""
        team = NHLTeam(self.team)
        games = team.unplayed_games
        num_games = self.args.get('games')
        emoji = self.emojis.get(str(team.name))
        if limit:
            games = games[:limit]
        elif num_games:
            games = games[:int(num_games)]
        if not title:
            reply = []
        else:
            reply = [f":{emoji}: *{team.name} Upcoming Games*"]

        for game in games:
            date = self._format_date(game['date'])
            away_team = game['away_team']['name']
            home_team = game['home_team']['name']
            if 'Canadiens' in away_team:
                away_team = 'Montreal Canadiens'
            elif 'Canadiens' in home_team:
                home_team = 'Montreal Canadiens'
            away_emoji = self.emojis.get(away_team.lower())
            home_emoji = self.emojis.get(home_team.lower())
            game_message = [
                f"*{date}*",
                f">*:{away_emoji}: {away_team} vs :{home_emoji}: {home_team}*\n"
            ]
            reply.append("\n".join(game_message))
        return "\n".join(reply)

    def nhl_league_schedule(self, title=True, limit=None, type=None):
        """Format slack reply"""
        nhl = NHL()
        if not nhl.todays_games:
            return f":nhl: *_No Games Today*_"
        games = nhl.todays_games['games']
        date = self._format_date(nhl.todays_games['date'])
        if not title:
            reply = []
        else:
            reply = [f":nhl: *Games on {date}*"]

        for i in range(len(games)):
            away_team = games[i]['teams']['away']['team']['name']
            away_record = games[i]['teams']['away']['leagueRecord']
            home_team = games[i]['teams']['home']['team']['name']
            home_record = games[i]['teams']['home']['leagueRecord']
            if 'Canadiens' in away_team:
                away_team = 'Montreal Canadiens'
            elif 'Canadiens' in home_team:
                home_team = 'Montreal Canadiens'
            away_emoji = self.emojis.get(away_team.lower())
            home_emoji = self.emojis.get(home_team.lower())
            game_message = [
                f">*:{away_emoji}: {away_team} `{away_record['wins']}-{away_record['losses']}-{away_record['ot']}`*",
                f">*:{home_emoji}: {home_team} `{home_record['wins']}-{home_record['losses']}-{home_record['ot']}`*\n"
            ]
            reply.append("\n".join(game_message))
        return "\n".join(reply)

    def nhl_league_scores(self):
        nhl = NHLLeague()
        if not nhl.live_scores and not nhl.recent_scores:
            return f":nhl: *_No recent scores*_"
        if not nhl.live_scores:
            games = nhl.recent_scores
        else:
            games = nhl.live_scores
        game_date = self._format_date(games[0]['date'])
        reply = [f":nhl: *Recent Scores*\n*{game_date}*"]
        for i in range(len(games)):
            date = self._format_date(games[i]['date'])
            away_team = games[i]['away_team']['name']
            home_team = games[i]['home_team']['name']
            if 'Canadiens' in away_team:
                away_team = 'Montreal Canadiens'
            elif 'Canadiens' in home_team:
                home_team = 'Montreal Canadiens'
            away_score = games[i]['away_team']['score']
            away_emoji = self.emojis.get(away_team.lower())
            home_score = games[i]['home_team']['score']
            home_emoji = self.emojis.get(home_team.lower())
            if date != game_date:
                game_message = [
                    f"*{date}*",
                    f">:{away_emoji}: *{away_team}:* *`{away_score}`*",
                    f">:{home_emoji}: *{home_team}:* *`{home_score}`*\n"
                ]
            else:
                game_message = [
                    f">:{away_emoji}: *{away_team}:* *`{away_score}`*",
                    f">:{home_emoji}: *{home_team}:* *`{home_score}`*\n"
                ]
            reply.append("\n".join(game_message))
        return "\n".join(reply)

    def nhl_team_scores(self, title=True, limit=None):
        """Format slack reply"""
        team = NHLTeam(self.team)
        games = team.game_results
        emoji = self.emojis.get(str(team.team_id))
        num_games = self.args.get('games')
        if limit:
            limit = len(games) - int(limit)
            games = games[limit:]
        elif num_games:
            limit = len(games) - int(num_games)
            games = games[limit:]
        if not title:
            reply = []
        else:
            reply = [f":{emoji}: *{team.name} Scores*"]

        for i in range(len(games)):
            date = self._format_date(games[i]['date'])
            away_team = games[i]['away_team']['name']
            home_team = games[i]['home_team']['name']
            if 'Canadiens' in away_team:
                away_team = 'Montreal Canadiens'
            elif 'Canadiens' in home_team:
                home_team = 'Montreal Canadiens'
            away_score = games[i]['away_team']['score']
            away_emoji = self.emojis.get(away_team.lower())
            home_score = games[i]['home_team']['score']
            home_emoji = self.emojis.get(home_team.lower())
            game_message = [
                f"*{date}*",
                f">:{away_emoji}: *{away_team}:* *`{away_score}`*",
                f">:{home_emoji}: *{home_team}:* *`{home_score}`*\n"
            ]
            reply.append("\n".join(game_message))
        return "\n".join(reply)

    def nhl_standings(self):
        division = self.args.get('division')
        conference = self.args.get('conference')
        if not division and not conference:
            return self.nhl_league_standings()
        elif conference:
            return self.nhl_conference_standings()
        elif division:
            return self.nhl_division_standings()

    def nhl_division_standings(self):
        standings = self.nhl.standings['division']
        records = self.nhl.standings['records']
        reply = []
        division_emojis = {
            'Metropolitan': 'nhl_met',
            'Atlantic': 'nhl_atl',
            'Central': 'nhl_cen',
            'Pacific': 'nhl_pac'
        }
        for division, teams in standings.items():
            div_emoji = division_emojis.get(division)
            standings = [f":{div_emoji}: *{division} Division*"]
            sorted_teams = sorted(teams.items(), key=lambda k: int(k[1]))
            for team in sorted_teams:
                name, rank = team
                emoji = self.emojis.get(self.get_team_id(name))
                record = records.get(name)
                if len(rank) == 1:
                    standings.append(f">*{rank}  :{emoji}:  `{record}`*")
                else:
                    standings.append(f">*{rank} :{emoji}:  `{record}`*")
            reply.append("\n".join(standings))
        return "\n".join(reply)

    def nhl_conference_standings(self):
        """
        Build and return Slack formatted reply for NHL conference standings
        """
        conference_standings = self.nhl.standings['conference']
        records = self.nhl.standings['records']
        reply = []
        for conference, teams in conference_standings.items():
            if conference == 'Eastern':
                conf_emoji = 'nhl_east'
            else:
                conf_emoji = 'nhl_west'
            standings = [f":{conf_emoji}: *{conference} Conference Standings*"]
            sorted_teams = sorted(teams.items(), key=lambda k: int(k[1]))
            for team in sorted_teams:
                name, rank = team
                emoji = self.emojis.get(self.get_team_id(name))
                record = records.get(name)
                if len(rank) == 1:
                    standings.append(f">*{rank}  :{emoji}:  `{record}`*")
                else:
                    standings.append(f">*{rank} :{emoji}:  `{record}`*")
            reply.append("\n".join(standings))
        return "\n".join(reply)

    def nhl_league_standings(self):
        standings = self.nhl.standings['league']
        records = self.nhl.standings['records']
        reply = [f":nhl: *Current League Standings*"]
        sorted_standings = sorted(standings.items(), key=lambda k: int(k[1]))
        for team in sorted_standings:
            name, rank = team
            emoji = self.emojis.get(self.get_team_id(name))
            record = records.get(name)
            if len(rank) == 1:
                reply.append(f">*{rank}  :{emoji}:  `{record}`*")
            else:
                reply.append(f">*{rank} :{emoji}:  `{record}`*")
        return "\n".join(reply)

    def get_team_id(self, team):
        if 'Canadiens' in team:
            team = 'Montreal Canadiens'
        team_ids = self.config['teams']
        team_id = team_ids.get(team.lower())
        return str(team_id)

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
