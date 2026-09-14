import requests
import json
import os
from dotenv import load_dotenv
from model_poisson import calculate_1x2_probs
from utils import get_standard_name

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv('ODDS_API_KEY')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


# Dispatch formatted ticket alerts directly to Telegram
def send_telegram_msg(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("[!] Telegram credentials missing from .env, cannot dispatch alert.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            print("[INFO] Tickets successfully sent to Telegram!")
        else:
            print(f"[!] Telegram API error (Code {response.status_code}): {response.text}")
    except Exception as e:
        print(f"[!] Telegram network error: {e}")


# Supported tournament keys for The Odds API
SPORTS = [
    'soccer_epl', 'soccer_spain_la_liga', 'soccer_italy_serie_a',
    'soccer_germany_bundesliga', 'soccer_france_ligue_one',
    'soccer_fifa_world_cup', 'soccer_uefa_euro',
    'soccer_uefa_champs_league_qualification',
    'soccer_conmebol_copa_libertadores',
    'soccer_sweden_allsvenskan',
    'soccer_brazil_campeonato',
    'soccer_usa_mls',
    'soccer_norway_eliteserien'
]


def find_top_tickets(matches, target_odds, tolerance=0.5, top_n=3, max_overlap=1, min_matches=2):
    valid_tickets = []

    # Backtracking engine to bundle selections matching target odds within tolerance
    def backtrack(index, current_ticket, current_odds, current_prob, current_matches_set):
        if current_odds > target_odds + tolerance:
            return

        if abs(current_odds - target_odds) <= tolerance:
            if len(current_ticket) >= min_matches:
                valid_tickets.append({
                    'ticket': list(current_ticket),
                    'odds': current_odds,
                    'prob': current_prob
                })

        for i in range(index, len(matches)):
            bet = matches[i]
            if bet['match'] in current_matches_set: continue

            current_ticket.append(bet)
            current_matches_set.add(bet['match'])
            backtrack(i + 1, current_ticket, current_odds * bet['odds'], current_prob * bet['prob'],
                      current_matches_set)
            current_ticket.pop()
            current_matches_set.remove(bet['match'])

    backtrack(0, [], 1.0, 1.0, set())
    valid_tickets.sort(key=lambda x: x['prob'], reverse=True)

    diverse_tickets = []
    for t in valid_tickets:
        if len(diverse_tickets) == top_n:
            break

        current_match_names = {bet['match'] for bet in t['ticket']}
        is_too_similar = False

        for selected_t in diverse_tickets:
            selected_match_names = {bet['match'] for bet in selected_t['ticket']}
            overlap = len(current_match_names.intersection(selected_match_names))

            if overlap > max_overlap:
                is_too_similar = True
                break

        if not is_too_similar:
            diverse_tickets.append(t)

    return diverse_tickets


def match_team_stats(team_name, stats_dict):
    # Normalize team names to match local statistical dictionary keys
    clean_name = get_standard_name(team_name).lower()
    for stat_name in stats_dict.keys():
        stat_name_lower = stat_name.lower()
        if clean_name in stat_name_lower or stat_name_lower in clean_name:
            return stats_dict[stat_name]
    return None


def salveaza_bilete(tickets_list, target_odds):
    # Save generated betting tickets to a local text file
    with open("bilete_generate.txt", "w", encoding="utf-8") as f:
        f.write(f"=== BILETE PENTRU COTA {target_odds:.2f} ===\n\n")
        for i, t in enumerate(tickets_list, 1):
            f.write(f"--- Varianta {i} ---\n")
            f.write(f"Cota reala: {t['odds']:.2f} | Probabilitate matematica: {t['prob'] * 100:.2f}%\n")
            for bet in t['ticket']:
                f.write(f"{bet['match']} | {bet['selection']} | {bet['odds']:.2f}\n")
            f.write("\n")
    print("\n[INFO] Tickets successfully saved to 'bilete_generate.txt'.")


if __name__ == "__main__":
    print("1. Loading historical statistics database...")
    try:
        with open('statistici_salvate.json', 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except FileNotFoundError:
        print("Error: Local statistics file missing!")
        exit()

    # --- CLI USER CONFIGURATION ---
    print("\n=== Step 1: League Configuration ===")
    choice_ligues = input("All leagues (1) or Custom Selection (2): ")
    if choice_ligues == '2':
        for i, sport in enumerate(SPORTS, 1): print(f"{i}. {sport}")
        selection = input("Chosen leagues (e.g., 1 3 5): ")
        indices = [int(i) - 1 for i in selection.split() if i.isdigit()]
        active_leagues = [SPORTS[i] for i in indices if 0 <= i < len(SPORTS)]
        if not active_leagues: active_leagues = SPORTS
    else:
        active_leagues = SPORTS

    print("\n=== Step 2: Ticket Profile ===")
    choice_odds = input("1.SAFE (2.0) 2.MEDIUM (5.0) 3.RISKY (15.0) 4.Custom: ")
    if choice_odds == '1':
        TARGET_ODDS, TOLERANCE = 2.0, 0.2
    elif choice_odds == '2':
        TARGET_ODDS, TOLERANCE = 5.0, 0.5
    elif choice_odds == '3':
        TARGET_ODDS, TOLERANCE = 15.0, 2.0
    elif choice_odds == '4':
        TARGET_ODDS = float(input("Target Odds: "))
        TOLERANCE = float(input("Tolerance: "))
    else:
        TARGET_ODDS, TOLERANCE = 5.0, 0.5

    choice_len = input("Ticket style: 1.Short (2-3 matches), 2.Long (4+ matches): ")
    MIN_MATCHES, MAX_OVERLAP = (4, 2) if choice_len == '2' else (2, 0)

    # --- EXECUTION & CALCULATION ---
    value_bets = []
    print("\nFetching live matches and running odds analysis...")

    for sport in active_leagues:
        url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds'
        params = {'apiKey': API_KEY, 'regions': 'eu', 'markets': 'h2h', 'oddsFormat': 'decimal'}
        response = requests.get(url, params=params)
        if response.status_code != 200: continue
        data = response.json()

        for game in data:
            home_team, away_team = game['home_team'], game['away_team']
            h_s, a_s = match_team_stats(home_team, stats), match_team_stats(away_team, stats)
            if not h_s or not a_s: continue

            # Poisson expected goals calculation
            h_xg = max(h_s['attack_home'] * a_s['defense_away'] * h_s['league_avg_h'], 0.25)
            a_xg = max(a_s['attack_away'] * h_s['defense_home'] * a_s['league_avg_a'], 0.25)
            probs = calculate_1x2_probs(h_xg, a_xg)
            probs['1X'], probs['X2'] = probs['1'] + probs['X'], probs['X'] + probs['2']

            # Extract bookmaker markets
            if not game.get('bookmakers'): continue
            market = next((m for m in game['bookmakers'][0]['markets'] if m['key'] == 'h2h'), None)
            if market:
                o1 = next((o['price'] for o in market['outcomes'] if o['name'] == home_team), 0)
                o2 = next((o['price'] for o in market['outcomes'] if o['name'] == away_team), 0)
                ox = next((o['price'] for o in market['outcomes'] if o['name'] == 'Draw'), 0)

                if o1 and ox and o2:
                    pariuri = [
                        {"selection": "1", "odds": o1, "prob": probs['1']},
                        {"selection": "X", "odds": ox, "prob": probs['X']},
                        {"selection": "2", "odds": o2, "prob": probs['2']},
                        {"selection": "1X", "odds": (o1 * ox) / (o1 + ox), "prob": probs['1X']},
                        {"selection": "X2", "odds": (o2 * ox) / (o2 + ox), "prob": probs['X2']}
                    ]
                    for p in pariuri:
                        if p['odds'] * p['prob'] > 0.95 and p['prob'] > (0.6 if 'X' in p['selection'] else 0.4):
                            value_bets.append(
                                {"match": f"{home_team} vs {away_team}", **p, "value": p['odds'] * p['prob']})

    # --- TICKET GENERATION & OUTPUT ---
    value_bets.sort(key=lambda x: x['prob'] if choice_len == '2' else x['value'], reverse=True)
    top_tickets = find_top_tickets(value_bets[:40], TARGET_ODDS, TOLERANCE, top_n=3, max_overlap=MAX_OVERLAP,
                                   min_matches=MIN_MATCHES)

    if top_tickets:
        msg = f"⚽ *GENERATED TICKETS (Odds: {TARGET_ODDS:.2f})*\n\n"
        for i, t in enumerate(top_tickets, 1):
            msg += f"*Variant {i}* (Odds: {t['odds']:.2f})\n"
            for bet in t['ticket']:
                msg += f"{bet['match']} | {bet['selection']} | {bet['odds']:.2f}\n"
                msg += "\n"

        print("\n=== YOUR GENERATED TICKETS ===")
        print(msg.replace('*', '').replace('`', ''))  # Print clean formatting to terminal
        send_telegram_msg(msg)
        salveaza_bilete(top_tickets, TARGET_ODDS)
    else:
        print("\n[!] No valid betting tickets found matching the criteria.")