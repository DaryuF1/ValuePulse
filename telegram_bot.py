import requests
import os
from dotenv import load_dotenv
from model_poisson import calculate_1x2_probs
from utils import get_standard_name
import json

# Load environment variables from the local .env file
load_dotenv()

API_KEY = os.getenv('FOOTBALL_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


def send_telegram_msg(message):
    # Dispatch notification payload to Telegram chat
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("Message sent successfully!")
        else:
            print(f"Telegram error (Code {response.status_code}): {response.text}")
    except Exception as e:
        print(f"Network error: {e}")


def get_stats_for_team(team_name, stats_dict):
    # Fuzzy match team names against local statistics database
    clean_name = get_standard_name(team_name).lower()
    for stat_name in stats_dict.keys():
        stat_name_lower = stat_name.lower()
        if clean_name in stat_name_lower or stat_name_lower in clean_name:
            return stats_dict[stat_name]
    return None


def run_bot():
    # Load team statistics database
    try:
        with open('statistici_salvate.json', 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except FileNotFoundError:
        print("Error: 'statistici_salvate.json' database file missing.")
        return

    leagues = {"Premier League": 39, "Brazilia A": 71}
    final_message = "⚽ *Weekend Predictions:*\n\n"
    meciuri_gasite = False

    for name, id_league in leagues.items():
        url = "https://v3.football.api-sports.io/fixtures"
        # Use status="FT" for testing finished matches, or "NS" (Not Started) for live upcoming ones
        params = {"league": id_league, "season": "2026", "status": "NS"}

        try:
            response = requests.get(url, headers={"x-apisports-key": API_KEY}, params=params)
            fixtures = response.json().get('response', [])
        except Exception as e:
            print(f"API error for {name}: {e}")
            continue

        lista_meciuri = ""
        for f in fixtures[:5]:
            h = f['teams']['home']['name']
            a = f['teams']['away']['name']

            h_s, a_s = get_stats_for_team(h, stats), get_stats_for_team(a, stats)
            if not h_s or not a_s: continue

            # Poisson expected goals model calculation
            h_xg = max(h_s['attack_home'] * a_s['defense_away'] * h_s['league_avg_h'], 0.25)
            a_xg = max(a_s['attack_away'] * h_s['defense_home'] * a_s['league_avg_a'], 0.25)
            probs = calculate_1x2_probs(h_xg, a_xg)
            if abs(h_xg - a_xg) < 0.35: probs['X'] += 0.15

            pred = max(probs, key=probs.get)
            lista_meciuri += f"{h[:10]} vs {a[:10]} -> *{pred}*\n"

        # Append league block only if fixtures were successfully processed
        if lista_meciuri:
            final_message += f"--- {name} ---\n{lista_meciuri}\n"
            meciuri_gasite = True

    # Send summary alert via Telegram if any matches were found
    if meciuri_gasite:
        send_telegram_msg(final_message)
    else:
        print("No matching fixtures found to trigger notification.")


if __name__ == "__main__":
    run_bot()