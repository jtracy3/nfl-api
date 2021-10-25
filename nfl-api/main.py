from espn.client import NFLClient
from pprint import pprint

# if r.status_code == 200:
#     print("Succesful request")
# else:
#     raise Exception("Unsuccessful request")

nfl_client = NFLClient()
# pprint(nfl.get_week_games(season=2021, week=1))
# pprint(nfl_client.get_game_details(game_id="401326423"))
# pprint(nfl_client.get_game_id(date="20211024", team="San Francisco"))
# pprint(nfl_client.get_team_id("LAC"))
# pprint(nfl_client.get_team_schedule(team_id="3", season=2019, season_type=2))
# pprint(nfl_client.get_teams())
pprint(nfl_client.get_odds(game_id="401326315"))