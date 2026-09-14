import streamlit as st
import datetime
import json
import os
from dotenv import load_dotenv
from model_poisson import calculate_1x2_probs
import requests
from utils import get_standard_name

# --- App Configuration & Environment Setup ---
load_dotenv()

# Citim cheile din st.secrets (pe Streamlit Cloud) sau din os.getenv (local)
API_KEY = (
    st.secrets.get("ODDS_API_KEY")
    if "ODDS_API_KEY" in st.secrets
    else os.getenv("ODDS_API_KEY")
)
FOOTBALL_API_KEY = (
    st.secrets.get("FOOTBALL_API_KEY")
    if "FOOTBALL_API_KEY" in st.secrets
    else os.getenv("FOOTBALL_API_KEY")
)
TELEGRAM_TOKEN = (
    st.secrets.get("TELEGRAM_TOKEN")
    if "TELEGRAM_TOKEN" in st.secrets
    else os.getenv("TELEGRAM_TOKEN")
)
CHAT_ID = (
    st.secrets.get("TELEGRAM_CHAT_ID")
    if "TELEGRAM_CHAT_ID" in st.secrets
    else os.getenv("TELEGRAM_CHAT_ID")
)

BIN_ID = (
    st.secrets.get("JSONBIN_ID")
    if "JSONBIN_ID" in st.secrets
    else os.getenv("JSONBIN_ID")
)
API_KEY_JB = (
    st.secrets.get("JSONBIN_KEY")
    if "JSONBIN_KEY" in st.secrets
    else os.getenv("JSONBIN_KEY")
)

# Initialize session state for persistent rendering across UI interactions
if "top_tickets" not in st.session_state:
  st.session_state.top_tickets = None

# Comprehensive active leagues mapping for The Odds API
SPORTS = {
    "Premier League": "soccer_epl",
    "La Liga": "soccer_spain_la_liga",
    "Serie A": "soccer_italy_serie_a",
    "Bundesliga": "soccer_germany_bundesliga",
    "Ligue 1": "soccer_france_ligue_one",
    "România Liga 1": "soccer_romania_liga_1",
    "World Cup": "soccer_fifa_world_cup",
    "Euro": "soccer_uefa_euro",
    "Champions League": "soccer_uefa_champs_league_qualification",
    "Copa Libertadores": "soccer_conmebol_copa_libertadores",
    "Allsvenskan": "soccer_sweden_allsvenskan",
    "Brazil A": "soccer_brazil_campeonato",
    "MLS": "soccer_usa_mls",
    "Norway Eliteserien": "soccer_norway_eliteserien",
}


# --- Helper Functions ---


def send_telegram_msg(message):
  if not TELEGRAM_TOKEN or not CHAT_ID:
    return "Missing credentials"
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
  try:
    response = requests.post(url, data=payload)
    return response.status_code
  except Exception as e:
    return str(e)


def match_team_stats(team_name, stats_dict):
  clean_name = get_standard_name(team_name).lower()
  for stat_name, s in stats_dict.items():
    stat_name_lower = stat_name.lower()
    if clean_name in stat_name_lower or stat_name_lower in clean_name:
      return s
  return None


def find_top_tickets(
    matches, target_odds, tolerance, top_n, max_overlap, min_matches
):
  valid_tickets = []

  def backtrack(
      index, current_ticket, current_odds, current_prob, current_matches_set
  ):
    if current_odds > target_odds + tolerance:
      return
    if (
        abs(current_odds - target_odds) <= tolerance
        and len(current_ticket) >= min_matches
    ):
      valid_tickets.append({
          "ticket": list(current_ticket),
          "odds": current_odds,
          "prob": current_prob,
      })
    for i in range(index, len(matches)):
      bet = matches[i]
      if bet["match"] in current_matches_set:
        continue
      current_ticket.append(bet)
      current_matches_set.add(bet["match"])
      backtrack(
          i + 1,
          current_ticket,
          current_odds * bet["odds"],
          current_prob * bet["prob"],
          current_matches_set,
      )
      current_ticket.pop()
      current_matches_set.remove(bet["match"])

  backtrack(0, [], 1.0, 1.0, set())
  valid_tickets.sort(key=lambda x: x["prob"], reverse=True)

  diverse_tickets = []
  for t in valid_tickets:
    if len(diverse_tickets) == top_n:
      break
    current_match_names = {bet["match"] for bet in t["ticket"]}
    is_too_similar = False
    for selected_t in diverse_tickets:
      selected_match_names = {bet["match"] for bet in selected_t["ticket"]}
      overlap = len(current_match_names.intersection(selected_match_names))
      if overlap > max_overlap:
        is_too_similar = True
        break
    if not is_too_similar:
      diverse_tickets.append(t)

  return diverse_tickets


# --- Funcții Stocare Cloud (JSONBin) ---


def incarca_istoric():
  if not BIN_ID or not API_KEY_JB:
    return []
  url = f"https://api.jsonbin.io/v3/b/{BIN_ID}/latest"
  headers = {"X-Master-Key": API_KEY_JB}
  try:
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
      return res.json().get("record", [])
  except:
    pass
  return []


def salveaza_istoric(istoric):
  if not BIN_ID or not API_KEY_JB:
    return
  url = f"https://api.jsonbin.io/v3/b/{BIN_ID}"
  headers = {"Content-Type": "application/json", "X-Master-Key": API_KEY_JB}
  try:
    requests.put(url, headers=headers, json=istoric)
  except:
    pass


def salveaza_bilet_istoric(ticket_data):
  istoric = incarca_istoric()
  bilet_entry = {
      "id": len(istoric) + 1,
      "data": datetime.date.today().strftime("%Y-%m-%d"),
      "cota": ticket_data["odds"],
      "probabilitate": ticket_data["prob"],
      "status": "În desfășurare",
      "ticket": ticket_data["ticket"],
  }
  istoric.append(bilet_entry)
  salveaza_istoric(istoric)


def verifica_status_bilete():
  istoric = incarca_istoric()
  if not istoric:
    return []

  headers = {"x-apisports-key": FOOTBALL_API_KEY} if FOOTBALL_API_KEY else {}
  updated = False

  for bilet in istoric:
    if bilet["status"] != "În desfășurare":
      continue

    bilet_pierdut = False
    toate_meciurile_terminate = True

    for bet in bilet["ticket"]:
      teams = bet["match"].split(" vs ")
      if len(teams) != 2:
        toate_meciurile_terminate = False
        continue
      home_t, away_t = teams[0].strip(), teams[1].strip()

      url = "https://v3.football.api-sports.io/fixtures"
      params = {"search": home_t, "status": "FT", "season": "2026"}
      try:
        res = requests.get(url, headers=headers, params=params, timeout=5)
        if res.status_code == 200:
          fixtures = res.json().get("response", [])
          match_found = False
          rezultat_corect = False
          for f in fixtures:
            h_name = f["teams"]["home"]["name"]
            a_name = f["teams"]["away"]["name"]
            if (
                home_t.lower() in h_name.lower()
                or away_t.lower() in a_name.lower()
            ):
              match_found = True
              hg = f["goals"]["home"]
              ag = f["goals"]["away"]
              if hg is None or ag is None:
                match_found = False
                break

              sel = bet["selection"]
              if sel == "1" and hg > ag:
                rezultat_corect = True
              elif sel == "2" and ag > hg:
                rezultat_corect = True
              elif sel == "X" and hg == ag:
                rezultat_corect = True
              elif sel == "1X" and hg >= ag:
                rezultat_corect = True
              elif sel == "X2" and ag >= hg:
                rezultat_corect = True
              break

          if not match_found:
            toate_meciurile_terminate = False
          elif not rezultat_corect:
            bilet_pierdut = True
      except:
        toate_meciurile_terminate = False

    if bilet_pierdut:
      bilet["status"] = "❌ Pierdut"
      updated = True
    elif toate_meciurile_terminate and not bilet_pierdut:
      bilet["status"] = "✅ Câștigat"
      updated = True

  if updated:
    salveaza_istoric(istoric)

  return istoric


# --- Streamlit UI Layout ---
st.set_page_config(page_title="PariuBot - Generator Bilete", layout="wide")
st.title("⚽ PariuBot - Generator Inteligent și Istoric Bilete")

with st.sidebar:
  st.header("Configurare Pariu")
  mode = st.radio("Selecție Ligi", ["Toate ligile", "Selectează manual"])

  active_leagues = list(SPORTS.values())
  if mode == "Selectează manual":
    selected_names = st.multiselect(
        "Alege ligile active", list(SPORTS.keys()), default=["Premier League"]
    )
    active_leagues = [SPORTS[name] for name in selected_names]

  profile = st.selectbox(
      "Profil Bilet", ["SAFE (2.0)", "MEDIUM (5.0)", "RISKY (15.0)", "Personalizat"]
  )

  if profile == "Personalizat":
    target_odds = st.number_input(
        "Cota țintă", min_value=1.1, max_value=100.0, value=5.0
    )
    tolerance = st.number_input(
        "Toleranță cotă (+/-)", min_value=0.05, max_value=5.0, value=0.5
    )
  else:
    target_odds, tolerance = {
        "SAFE (2.0)": (2.0, 0.2),
        "MEDIUM (5.0)": (5.0, 0.5),
        "RISKY (15.0)": (15.0, 2.0),
    }[profile]

  bet_style = st.radio(
      "Stil Bilet", ["Scurt (2-3 meciuri)", "Lung (4+ meciuri)"]
  )
  generate_btn = st.button("🚀 Generează Bilete", type="primary")

# --- Core Processing Logic ---
if generate_btn:
  st.session_state.top_tickets = None

  if not os.path.exists("statistici_salvate.json"):
    st.error("Eroare: Lipsește fișierul 'statistici_salvate.json'!")
    st.stop()

  with open("statistici_salvate.json", "r", encoding="utf-8") as f:
    stats = json.load(f)

  min_matches, max_overlap = (4, 2) if "Lung" in bet_style else (2, 0)

  value_bets = []
  with st.spinner("Se descarcă cotele live și se rulează motorul Poisson..."):
    for sport in active_leagues:
      url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
      params = {
          "apiKey": API_KEY,
          "regions": "eu",
          "markets": "h2h",
          "oddsFormat": "decimal",
      }
      try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code != 200:
          continue
        data = response.json()

        for game in data:
          home_team, away_team = game["home_team"], game["away_team"]
          h_s = match_team_stats(home_team, stats)
          a_s = match_team_stats(away_team, stats)
          if not h_s or not a_s:
            continue

          # Poisson expected goals calculation
          h_xg = max(
              h_s["attack_home"] * a_s["defense_away"] * h_s["league_avg_h"],
              0.25,
          )
          a_xg = max(
              a_s["attack_away"] * h_s["defense_home"] * a_s["league_avg_a"],
              0.25,
          )
          probs = calculate_1x2_probs(h_xg, a_xg)
          probs["1X"] = probs["1"] + probs["X"]
          probs["X2"] = probs["X"] + probs["2"]

          if not game.get("bookmakers"):
            continue
          market = next(
              (
                  m
                  for m in game["bookmakers"][0]["markets"]
                  if m["key"] == "h2h"
              ),
              None,
          )
          if market:
            o1 = next(
                (
                    o["price"]
                    for o in market["outcomes"]
                    if o["name"] == home_team
                ),
                0,
            )
            o2 = next(
                (
                    o["price"]
                    for o in market["outcomes"]
                    if o["name"] == away_team
                ),
                0,
            )
            ox = next(
                (o["price"] for o in market["outcomes"] if o["name"] == "Draw"),
                0,
            )

            if o1 and ox and o2:
              pariuri = [
                  {"selection": "1", "odds": o1, "prob": probs["1"]},
                  {"selection": "X", "odds": ox, "prob": probs["X"]},
                  {"selection": "2", "odds": o2, "prob": probs["2"]},
                  {
                      "selection": "1X",
                      "odds": (o1 * ox) / (o1 + ox),
                      "prob": probs["1X"],
                  },
                  {
                      "selection": "X2",
                      "odds": (o2 * ox) / (o2 + ox),
                      "prob": probs["X2"],
                  },
              ]
              for p in pariuri:
                if p["odds"] * p["prob"] > 0.95 and p["prob"] > (
                    0.6 if "X" in p["selection"] else 0.4
                ):
                  value_bets.append({
                      "match": f"{home_team} vs {away_team}",
                      "selection": p["selection"],
                      "odds": round(p["odds"], 2),
                      "prob": p["prob"],
                      "value": p["odds"] * p["prob"],
                  })
      except Exception as e:
        continue

  # Sort value bets based on strategy
  if "Lung" in bet_style:
    value_bets.sort(key=lambda x: x["prob"], reverse=True)
  else:
    value_bets.sort(key=lambda x: x["value"], reverse=True)

  top_tickets = find_top_tickets(
      value_bets[:40],
      target_odds,
      tolerance,
      top_n=3,
      max_overlap=max_overlap,
      min_matches=min_matches,
  )
  st.session_state.top_tickets = top_tickets

# --- Results Rendering ---
if st.session_state.top_tickets:
  st.success("Biletele au fost generate cu succes!")

  for i, t in enumerate(st.session_state.top_tickets, 1):
    st.subheader(
        f"Varianta {i} — Cota: {t['odds']:.2f} (Prob:"
        f" {t['prob'] * 100:.1f}%)"
    )

    table_data = []
    for bet in t["ticket"]:
      table_data.append({
          "Meci": bet["match"],
          "Selecție": bet["selection"],
          "Cota": f"{bet['odds']:.2f}",
      })
    st.table(table_data)

    col1, col2 = st.columns(2)
    with col1:
      if st.button(f"💾 Salvează în Istoric V{i}", key=f"save_hist_{i}"):
        salveaza_bilet_istoric(t)
        st.success(f"Varianta {i} a fost salvată în istoric pe cloud!")

    with col2:
      if st.button(f"Trimite Varianta {i} pe Telegram", key=f"btn_tel_{i}"):
        msg = f"⚽ *BILET RECOMANDAT (Cota: {t['odds']:.2f})*\n\n"
        for bet in t["ticket"]:
          msg += f"{bet['match']} | *{bet['selection']}* | {bet['odds']:.2f}\n"
        res = send_telegram_msg(msg)
        if res == 200:
          st.toast(f"Varianta {i} a fost trimisă pe Telegram!")
        else:
          st.error(f"Eroare trimitere Telegram: {res}")
else:
  if generate_btn:
    st.warning(
        "Nu s-au găsit meciuri care să respecte criteriile stricte pentru cota"
        " aleasă. Încearcă o toleranță mai mare sau alte ligi."
    )

# --- Secțiunea de Istoric și Verificare în pagină ---
st.divider()
st.subheader("📋 Istoric Bilete Salvate și Rezultate Live")
if st.button("🔄 Verifică Statusul Biletelor Salvate"):
  with st.spinner("Se interoghează rezultatele finale de la API..."):
    verifica_status_bilete()
    st.success("Verificare finalizată!")

saved_tickets = incarca_istoric()
if saved_tickets:
  for sb in saved_tickets:
    status_color = (
        "🟡"
        if sb["status"] == "În desfășurare"
        else ("🟢" if "Câștigat" in sb["status"] else "🔴")
    )
    with st.expander(
        f"Bilet #{sb['id']} | Dată: {sb['data']} | Cota: {sb['cota']:.2f} |"
        f" Status: {status_color} {sb['status']}"
    ):
      for b in sb["ticket"]:
        st.write(
            f"- {b['match']} | **{b['selection']}** (Cota: {b['odds']:.2f})"
        )
else:
  st.info("Nu există bilete salvate în istoric momentan.")
