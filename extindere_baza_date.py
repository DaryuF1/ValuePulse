import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv('FOOTBALL_API_KEY')
HEADERS = {"x-apisports-key": API_KEY}

# Supported leagues mapped to their respective API-Sports IDs
ACTIVE_LEAGUES = {
    "Premier League (Anglia)": 39,
    "Serie A (Brazilia)": 71,
    "MLS (SUA)": 253
}

def get_stats_for_team(team_name, stats_dict):
    # Fuzzy match local team names against saved database records
    clean_name = get_standard_name(team_name).lower()
    for stat_name in stats_dict.keys():
        stat_name_lower = stat_name.lower()
        if clean_name in stat_name_lower or stat_name_lower in clean_name:
            return stats_dict[stat_name]
    return None


def update_stats_for_league(league_id, league_name):
    print(f"Fetching standings and computing stats for {league_name}...")

    url = "https://v3.football.api-sports.io/standings"
    params = {"league": league_id, "season": "2024"}
    response = requests.get(url, headers=HEADERS, params=params)

    if response.status_code != 200:
        print(f"API Error: {response.status_code}")
        return

    data = response.json().get('response', [])
    if not data:
        print("No standings data received for this league.")
        return

    standings = data[0]['league']['standings'][0]

    # Aggregate goals to calculate overall league scoring baselines
    # API v3 returns 'for' and 'against' fields directly as integers
    total_goals_h = sum(t['home']['goals']['for'] for t in standings)
    total_goals_a = sum(t['away']['goals']['for'] for t in standings)
    num_teams = len(standings)

    # Normalize across 19 games (half a season standard block) for averages
    league_avg_h = (total_goals_h / num_teams) / 19
    league_avg_a = (total_goals_a / num_teams) / 19

    try:
        with open('statistici_salvate.json', 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except FileNotFoundError:
        stats = {}

    for team in standings:
        name = team['team']['name']

        # Extract home and away goal stats directly
        h_for = team['home']['goals']['for']
        h_against = team['home']['goals']['against']
        a_for = team['away']['goals']['for']
        a_against = team['away']['goals']['against']

        # Compute relative attack and defense multipliers
        attack_h = (h_for / 19) / league_avg_h if league_avg_h > 0 else 1
        attack_a = (a_for / 19) / league_avg_a if league_avg_a > 0 else 1

        defense_h = (h_against / 19) / league_avg_a if league_avg_a > 0 else 1
        defense_a = (a_against / 19) / league_avg_h if league_avg_h > 0 else 1

        stats[name] = {
            "attack_home": round(attack_h, 3),
            "attack_away": round(attack_a, 3),
            "defense_home": round(defense_h, 3),
            "defense_away": round(defense_a, 3),
            "league_avg_h": round(league_avg_h, 3),
            "league_avg_a": round(league_avg_a, 3)
        }

    with open('statistici_salvate.json', 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=4)

    print(f"Success! {league_name} stats successfully updated and saved.")


if __name__ == "__main__":
    # Run offline generator to refresh local JSON database
    update_stats_for_league(71, "Serie A Brazilia")
    update_stats_for_league(253, "MLS")
    print("Done! Local statistics database is ready.")