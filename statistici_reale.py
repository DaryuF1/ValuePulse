import requests
import json
import os
from dotenv import load_dotenv
from utils import get_standard_name

# Load API credentials from environment
load_dotenv()
FOOTBALL_API_KEY = os.getenv('FOOTBALL_API_KEY')
CACHE_STATS = 'statistici_salvate.json'

# Mapping between Odds API keys and API-Sports tournament IDs
LEAGUES_MAPPING = {
    'soccer_epl': 39,
    'soccer_spain_la_liga': 140,
    'soccer_italy_serie_a': 135,
    'soccer_germany_bundesliga': 78,
    'soccer_france_ligue_one': 61,
    'soccer_romania_liga_1': 283,
    'soccer_fifa_world_cup': 1,  # FIFA World Cup
    'soccer_uefa_euro': 4,  # UEFA European Championship (EURO)
    'soccer_uefa_champs_league_qualification': 2,  # Champions League
    'soccer_conmebol_copa_libertadores': 13,  # Copa Libertadores
    'soccer_sweden_allsvenskan': 113,  # Sweden Allsvenskan
    'soccer_brazil_campeonato': 71,  # Brazil Serie A
    'soccer_usa_mls': 253,  # USA MLS
    'soccer_norway_eliteserien': 69  # Norway Eliteserien
}


def match_team_stats(team_name, stats_dict):
    # Fuzzy match team names against local database records
    clean_name = get_standard_name(team_name).lower()
    for stat_name in stats_dict.keys():
        stat_name_lower = stat_name.lower()
        if clean_name in stat_name_lower or stat_name_lower in clean_name:
            return stats_dict[stat_name]
    return None


def fetch_all_stats(force_update=True):
    # Return local cached stats if available and force update is disabled
    if not force_update and os.path.exists(CACHE_STATS):
        print("Reading combined team statistics from local cache file...")
        with open(CACHE_STATS, 'r', encoding='utf-8') as f:
            return json.load(f)

    all_teams_stats = {}
    print("Fetching FRESH statistics for all configured leagues from API-Football...\n")
    url = "https://v3.football.api-sports.io/standings"
    headers = {"x-apisports-key": FOOTBALL_API_KEY}

    for odds_key, api_football_id in LEAGUES_MAPPING.items():
        print(f"-> Processing league: {odds_key} (ID {api_football_id})...")

        # Fallback across recent seasons down to 2022 to capture tournaments like World Cup
        seasons_to_try = [2026, 2025, 2024, 2023, 2022]
        data = None
        used_season = None

        for season in seasons_to_try:
            querystring = {"league": str(api_football_id), "season": str(season)}
            response = requests.get(url, headers=headers, params=querystring)

            if response.status_code == 200:
                resp_json = response.json()
                if resp_json.get('response'):
                    data = resp_json
                    used_season = season
                    break

        if not data or not data.get('response'):
            print(f"   [!] Missing data for league {api_football_id} in recent years.")
            continue

        print(f"   [✓] Data successfully found for season {used_season}.")
        all_standings = data['response'][0]['league']['standings']

        total_h, total_a, games_h, games_a = 0, 0, 0, 0

        # 1. Compute aggregate league scoring averages (safely handling None values)
        for group in all_standings:
            total_h += sum((t['home']['goals']['for'] or 0) for t in group)
            total_a += sum((t['away']['goals']['for'] or 0) for t in group)
            games_h += sum((t['home']['played'] or 0) for t in group)
            games_a += sum((t['away']['played'] or 0) for t in group)

        games_h = games_h if games_h > 0 else 1
        games_a = games_a if games_a > 0 else 1

        l_avg_h = total_h / games_h
        l_avg_a = total_a / games_a

        # 2. Compute individual team attack and defense strengths
        for group in all_standings:
            for team in group:
                name = team['team']['name']

                # Sanitize fields against None values
                p_h = team['home']['played'] or 0
                p_a = team['away']['played'] or 0
                hp = p_h if p_h > 0 else 1
                ap = p_a if p_a > 0 else 1

                gf_h = team['home']['goals']['for'] or 0
                ga_h = team['home']['goals']['against'] or 0
                gf_a = team['away']['goals']['for'] or 0
                ga_a = team['away']['goals']['against'] or 0

                atk_h = (gf_h / hp) / l_avg_h if l_avg_h else 1.0
                def_a = (ga_a / ap) / l_avg_h if l_avg_h else 1.0
                atk_a = (gf_a / ap) / l_avg_a if l_avg_a else 1.0
                def_h = (ga_h / hp) / l_avg_a if l_avg_a else 1.0

                all_teams_stats[name] = {
                    'league_key': odds_key,
                    'league_avg_h': l_avg_h,
                    'league_avg_a': l_avg_a,
                    'attack_home': atk_h,
                    'defense_home': def_h,
                    'attack_away': atk_a,
                    'defense_away': def_a
                }

    with open(CACHE_STATS, 'w', encoding='utf-8') as f:
        json.dump(all_teams_stats, f, indent=4)

    return all_teams_stats


if __name__ == "__main__":
    stats = fetch_all_stats(force_update=True)
    print(f"\n[TOTAL SUCCESS] Database successfully updated!")
    print(f"Saved statistics for {len(stats)} teams into '{CACHE_STATS}'.")