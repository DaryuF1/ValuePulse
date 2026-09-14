import requests
import json
import os
from dotenv import load_dotenv

# Load API credentials from the local environment file
load_dotenv()
API_KEY = os.getenv('ODDS_API_KEY')
SPORT = 'soccer_epl'
CACHE_FILE = 'meciuri_salvate.json'

url = f'https://api.the-odds-api.com/v4/sports/{SPORT}/odds'
params = {
    'apiKey': API_KEY,
    'regions': 'eu',
    'markets': 'h2h',
    'oddsFormat': 'decimal'
}


def fetch_live_matches():
    # Read from local cache if it exists to save API request quota
    if os.path.exists(CACHE_FILE):
        print("Reading odds data from local cache file...")
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        print("Fetching fresh odds from the API...")
        response = requests.get(url, params=params)

        if response.status_code != 200:
            print(f"API Error: {response.status_code}\n{response.text}")
            return []

        data = response.json()

        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        print("Data successfully saved to 'meciuri_salvate.json'.")

    available_bets = []

    for game in data:
        if not game.get('bookmakers'): continue

        match_name = f"{game['home_team']} vs {game['away_team']}"
        first_bookmaker = game['bookmakers'][0]

        for market in first_bookmaker['markets']:
            if market['key'] == 'h2h':
                for outcome in market['outcomes']:
                    available_bets.append({
                        "match": match_name,
                        "selection": outcome['name'],
                        "odds": outcome['price'],
                        "prob": 0.50  # Placeholder probability, will be calculated later via Poisson
                    })

    return available_bets


if __name__ == "__main__":
    bets = fetch_live_matches()
    print(f"\nExtracted {len(bets)} betting options. Showing the first 6:\n")
    for bet in bets[:6]:
        print(f"Match: {bet['match']:<35} | Selection: {bet['selection']:<15} | Odds: {bet['odds']}")