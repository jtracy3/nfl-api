import datetime as dt
import requests
from typing import Union
from collections import OrderedDict
import re

from .constants import TEAM_IDS

class NFLClient:

    ## Reference https://gist.github.com/nntrn/ee26cb2a0716de0947a0a4e9a157bc1c
    
    SITE_VERSION = "v2"
    CORE_VERSION = "v2"
    WEB_VERSION = "v3"
    
    API_ESPN_SITE = "https://site.api.espn.com"
    API_ESPN_CORE = "https://sports.core.api.espn.com"

    # Core endpoints -------------------------------
    # season types -> 1: preseason 2: reg season 3: postseason
    WEEK_ENDPOINT = "/{}/sports/football/leagues/nfl/seasons/{}/types/2/weeks/{}"
    ODDS_ENDPOINT = "/{}/sports/football/leagues/nfl/events/{}/competitions/{}/odds"

    # Site endpoints ------------------------------
    SCOREBOARD_ENDPOINT = "/apis/site/{}/sports/football/nfl/scoreboard"
    SUMMARY_ENDPOINT = "/apis/site/{}/sports/football/nfl/summary"
    TEAM_SCHEDULE_ENDPOINT = "/apis/site/{}/sports/football/nfl/teams/{}/schedule"
    TEAMS_ENDPOINT = "/apis/site/{}/sports/football/nfl/teams"

    # Dates are in UTC
    DATE_FORMAT = "%Y-%m-%dT%H:%MZ"
    CONVERT_DATE_FORMAT = "%Y-%m-%y %H:%M:00"

    def __init__(self) -> None:
        self.session = requests.Session()

    @staticmethod
    def _check_two_city_team(team):
        if team.lower() == "los angeles" or team.lower() == "new york":
            raise Exception(f"""
                There a multiple teams with {team} in the name. Specify the team, e.g. Los Angeles Chargers
                """)

    @staticmethod
    def _match_team_name(team_input, team_check):
        team_input_l, team_check_l = team_input.lower(), team_check.lower()
        return team_input_l in team_check_l or team_input_l in re.split('\W', team_check_l)

    @staticmethod
    def _match_team_abbr(abbr_input, abbr_check):
        abbr_input_l, abbr_check_l = abbr_input.lower(), abbr_check.lower()
        return abbr_input_l in re.split('\W+', abbr_check_l)

    @staticmethod
    def _get_home_away(response: dict) -> dict:
        home_away = {}
        for team in response:
            home_away.update({
                team["homeAway"]: {
                    "id": team["id"],
                    "score": team["score"]["value"]
                }
            })
        return home_away
            

    @staticmethod
    def _convert_datetime_format(
        str_date: str, from_format: str, to_format: str
        ):
        return dt.datetime.strptime(str_date, from_format).strftime(to_format)

    def _get_week_start_end(self, season: int, week_number: int):
        url = self.API_ESPN_CORE + self.WEEK_ENDPOINT.format(self.CORE_VERSION, season, week_number)
        r = self.session.get(url).json()
        start = dt.datetime.strptime(r["startDate"], self.DATE_FORMAT).strftime("%Y%m%d")
        end = dt.datetime.strptime(r["endDate"], self.DATE_FORMAT).strftime("%Y%m%d")
        return start, end

    def get_week_games(self, season: Union[int, str], week: Union[int, str]):
        """
        Get all games for a given week during the season
        """

        url = self.API_ESPN_SITE + self.SCOREBOARD_ENDPOINT.format(self.SITE_VERSION)
        
        start, end = self._get_week_start_end(season, week)
        params = {"limit": 1000, "dates": f"{start}-{end}"}
        r = self.session.get(url, params=params)

        events = r.json()["events"]
        games = []
        for event in events:
            games.append(
                OrderedDict(
                    id=event["id"],
                    dateTime=self._convert_datetime_format(event.get("date"), self.DATE_FORMAT, self.CONVERT_DATE_FORMAT),
                    name=event["name"],
                    shortName=event["shortName"],
                    week=week
                )
            )
        return games

    def get_game_details(self, game_id: Union[int, str]):
        """
        Get game details
        """

        url = self.API_ESPN_SITE + self.SUMMARY_ENDPOINT.format(self.SITE_VERSION)
        params = {"event": game_id}
        
        r = self.session.get(url, params=params)
        
        team_boxscores = r.json()["boxscore"]["teams"]
        teams = []
        for team in team_boxscores:
            record = OrderedDict(gameId=game_id, teamId=team["team"]["id"])
            while team["statistics"]:
                stat = team["statistics"].pop(0)
                record |= OrderedDict({stat["name"]: stat["displayValue"]})
            teams.append(record)

        return teams

    def get_game_id(self, date: Union[dt.date, str], team: str):
        """
        Get game id for team on a given date. For the team parameter
        either send the full name, partial name or team abbreviation

        date format "%Y%m%d"
        """

        self._check_two_city_team(team)

        # TODO: maybe add help for datetime
        if type(date) is dt.date:
            date = date.strftime("%Y%m%d")

        url = self.API_ESPN_SITE + self.SCOREBOARD_ENDPOINT.format(self.SITE_VERSION)
        r = self.session.get(url, params={"dates": date})
        
        events = r.json()["events"]
        unmatched = True
        while unmatched and events:
            event = events.pop()
            # if full name, e.g. Los Angeles Chargers check full name else check parts, i.e. Los Angeles OR Chargers
            name, abbr = event["name"], event["shortName"]
            match_on_name = self._match_team_name(team, name)
            match_on_abbr = self._match_team_abbr(team, abbr)
            if match_on_name | match_on_abbr:
                game_id = event["id"]
                unmatched = False

        if unmatched:
            return print(f"Unable to find game for team: {team} on date: {date}")

        return game_id
        
    def get_team_id(self, team_name: str):
        """
        Get team id for a team based on the team name/abbreviation
        """
        self._check_two_city_team()
        
        team_name_l = team_name.lower()
        for k, v in TEAM_IDS.items():
            if team_name_l in v:
                return k
        return print(f"{team_name} id not found")

    def get_team_schedule(
        self, team_id: Union[int, str], season: Union[int, str], season_type: Union[int, str]=2
        ):

        url = self.API_ESPN_SITE + self.TEAM_SCHEDULE_ENDPOINT.format(self.SITE_VERSION, team_id)
        params = {"season": season, "seasontype": season_type}
        r = self.session.get(url, params=params)
        
        events = r.json()["events"]
        schedule = []
        for event in events:
            competitors = event["competitions"][0]["competitors"]
            record = OrderedDict(
                gameId=event["id"],
                dateTime=self._convert_datetime_format(event["date"], self.DATE_FORMAT, self.CONVERT_DATE_FORMAT),
                name=event["name"],
                shortName=event["shortName"],
                homeTeam=self._get_home_away(competitors)["home"]["id"],
                homeTeamScore=self._get_home_away(competitors)["home"]["score"],
                awayTeam=self._get_home_away(competitors)["away"]["id"],
                awayTeamScore=self._get_home_away(competitors)["away"]["score"],
                season=event["season"]["year"],
                seasonType=event["seasonType"]["id"],
                seasonTypeName=event["seasonType"]["name"],
                week=event["week"]["number"]
            )
            schedule.append(record)
        return schedule

    def get_teams(self):
        """
        Only includes teams for current season. For example, you won't find the San Diego
        Chargers nor the St. Louis Rams.
        """
        url = self.API_ESPN_SITE + self.TEAMS_ENDPOINT.format(self.SITE_VERSION)
        r = self.session.get(url)
        teams = r.json()["sports"][0]["leagues"][0]["teams"]
        
        teams_list = []
        for team in teams:
            team_ = team["team"]
            record = OrderedDict(
                id=team_["id"],
                slug=team_["slug"],
                location=team_["location"],
                name=team_["name"],
                nickname=team_["nickname"],
                abbreviation=team_["abbreviation"],
                displayName=team_["displayName"],
                shortDisplayName=team_["shortDisplayName"]
            )
            teams_list.append(record)
        
        return teams_list

    def get_odds(self, game_id: Union[int, str]):

        url = self.API_ESPN_CORE + self.ODDS_ENDPOINT.format(self.CORE_VERSION, game_id, game_id)
        r = self.session.get(url)
        odds_makers = r.json()["items"]

        odds_list = []
        for odds in odds_makers:
            record = OrderedDict(
                gameId=game_id,
                providerId=odds["provider"]["id"],
                providerName=odds["provider"]["name"],
                overUnder=odds.get("overUnder"),
                overOdds=odds.get("overOdds"),
                underOdds=odds.get("underOdds"),
                spread=odds.get("spread"),
                awayTeamMoneyLine=odds["awayTeamOdds"]["moneyLine"] if odds.get("awayTeamOdds") else None,
                awayTeamSpreadOdds=odds["awayTeamOdds"]["spreadOdds"] if odds.get("awayTeamOdds") else None,
                homeTeamMoneyLine=odds["homeTeamOdds"]["moneyLine"] if odds.get("homeTeamOdds") else None,
                homeTeamSpreadOdds=odds["homeTeamOdds"]["spreadOdds"] if odds.get("homeTeamOdds") else None
            )
            odds_list.append(record)
        
        return odds_list
