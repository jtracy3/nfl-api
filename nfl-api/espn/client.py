import datetime as dt
import requests
from typing import Match, Union
from collections import OrderedDict
import re

# from .constants import ALT_NAMES

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

    # Site endpoints ------------------------------
    SCOREBOARD_ENDPOINT = "/apis/site/{}/sports/football/nfl/scoreboard"
    SUMMARY_ENDPOINT = "/apis/site/{}/sports/football/nfl/summary"

    # Dates are in UTC
    DATE_FORMAT = "%Y-%m-%dT%H:%MZ"
    CONVERT_DATE_FORMAT = "%Y-%m-%y %H:%M:00"

    def __init__(self) -> None:
        self.session = requests.Session()

    def _get_week_start_end(self, season: int, week_number: int):
        url = self.API_ESPN_CORE + self.WEEK_ENDPOINT.format(self.CORE_VERSION, season, week_number)
        r = self.session.get(url).json()
        start = dt.datetime.strptime(r["startDate"], self.DATE_FORMAT).strftime("%Y%m%d")
        end = dt.datetime.strptime(r["endDate"], self.DATE_FORMAT).strftime("%Y%m%d")
        return start, end

    # TODO: add get function that gets and returns as JSON with status code
    def _get(url, params):
        pass

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
                    id=event.get("id"),
                    dateTime=self._convert_datetime_format(event.get("date"), self.DATE_FORMAT, self.CONVERT_DATE_FORMAT),
                    name=event.get("name"),
                    shortName=event.get("shortName"),
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
        r_json = r.json()
        
        team_boxscores = r_json["boxscore"]["teams"]
        teams = []
        for team in team_boxscores:
            record = OrderedDict(team_id=team["team"].get("id"))
            while team["statistics"]:
                stat = team["statistics"].pop(0)
                record |= OrderedDict({stat["name"]: stat["displayValue"]})
            teams.append(record)

        return teams

    def get_gameid(self, date: Union[dt.date, str], team: str):
        """
        Get game id for team on a given date. For the team parameter
        either send the full name, partial name or team abbreviation

        date format "%Y%m%d"
        """

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
            match_on_name = team.lower() in name.lower() or team.lower() in re.split('\W', name.lower())
            match_on_abbr = team.lower() in re.split('\W+', abbr.lower())
            if match_on_name | match_on_abbr:
                game_id = event["id"]
                unmatched = False

        if unmatched:
            return print(f"Unable to find game for team: {team} on date: {date}")

        return game_id
        

    @staticmethod
    def _convert_datetime_format(
        str_date: str, from_format: str, to_format: str
        ):
        return dt.datetime.strptime(str_date, from_format).strftime(to_format)