from espn.client import NFLClient
from pprint import pprint

# if r.status_code == 200:
#     print("Succesful request")
# else:
#     raise Exception("Unsuccessful request")

nfl_client = NFLClient()
# pprint(nfl.get_week_games(season=2021, week=1))
# pprint(nfl_client.get_game_details(game_id="401326423"))
pprint(nfl_client.get_gameid(date="20211017", team="Oakland"))
