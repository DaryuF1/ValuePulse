# utils.py

# Team mapping dictionary: Database/JSON name (left) -> The-Odds-API name (right)
TEAM_ALIASES = {
    # --- England ---
    "Brighton & Hove Albion": "Brighton and Hove Albion",
    "Tottenham Hotspur": "Tottenham Hotspur",
    "Manchester United": "Manchester United",
    "Newcastle United": "Newcastle United",

    # --- Spain ---
    "Real Betis": "Real Betis",
    "Athletic Club": "Athletic Bilbao",
    "Atletico Madrid": "Atlético Madrid",
    "Deportivo La Coruna": "Deportivo La Coruña",
    "Malaga": "Málaga",

    # --- Germany ---
    "Bayer Leverkusen": "Bayer Leverkusen",
    "Bayern Munchen": "Bayern Munich",
    "FC Koln": "1. FC Köln",
    "Schalke 04": "FC Schalke 04",
    "Hamburg": "Hamburger SV",
    "Paderborn": "SC Paderborn",
    "Elversberg": "Elversberg",
    "Borussia Monchengladbach": "Borussia Monchengladbach",

    # --- Italy ---
    "Sassuolo": "Sassuolo",
    "Frosinone": "Frosinone",

    # --- France ---
    "Le Mans": "Le Mans FC",
    "Lorient": "Lorient",
    "Troyes": "Troyes",

    # --- Sweden ---
    "Mjallby": "Mjällby AIF",
    "Hammarby": "Hammarby IF",
    "Orgryte": "Örgryte IS"
}


def get_standard_name(team_name):
    """
    Receives a team name from The-Odds-API and returns the standardized
    database name (matching API-Football format) for JSON lookup.
    """
    for key, value in TEAM_ALIASES.items():
        if team_name.lower() == key.lower() or team_name.lower() == value.lower():
            # Return the standard key (API-Football naming convention)
            return key

    # If the team is missing from the alias dictionary, return the original name as fallback
    return team_name