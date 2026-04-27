import psycopg2
import config
import requests
import hashlib

WFC_STATS_API = "http://localhost:8080/api/dummy_stats"
WFC_GROUPS_API = "https://api.wfc.wiilink.ca/api/groups"

def get_serial_prefixes(user_info):
    wiis = user_info.get("wiis")
    if not wiis:
        return []

    serials = []
    if isinstance(wiis, list):
        for wii in wiis:
            if isinstance(wii, dict):
                serial = wii.get("serial_number")
                if serial:
                    serials.append(serial)

    return [serial[:12] for serial in serials if serial]


def _build_serial_filter(column_name, serial_prefixes):
    if not serial_prefixes:
        return "", []
    clauses = " OR ".join([f"{column_name} LIKE %s" for _ in serial_prefixes])
    params = [f"{prefix}%" for prefix in serial_prefixes]
    return clauses, params


def _run_query(query, params, db_url=None):
    if db_url is None:
        db_url = config.db_url
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    cur.close()
    conn.close()
    return [dict(zip(columns, row)) for row in rows]


def fetch_wfc_game_data(gamespy_id):
    query = "SELECT * FROM titles WHERE gamespy_id = %s AND is_supported >= 1"
    result = _run_query(query, [gamespy_id], config.db_url)
    return result[0] if result else None

def fetch_featured_wfc_games():
    query = "SELECT * FROM titles WHERE is_featured = true AND is_supported >= 1"
    games = _run_query(query, [], config.db_url)
    
    try:
        resp = requests.get(WFC_STATS_API, timeout=10)
        resp.raise_for_status()
        stats = resp.json()
    except Exception as e:
        print(f"Error fetching WFC stats: {e}")
        stats = {}
        
    for game in games:
        gid = game.get("gamespy_id")
        if gid and gid in stats:
            stat = stats[gid]
            game["players_online"] = stat.get("online", 0)
            game["active"] = stat.get("active", 0)
            game["groups"] = stat.get("groups", 0)
            
    return games

def fetch_wfc_games():
    query = "SELECT * FROM titles WHERE is_supported >= 1 AND gamespy_id IS NOT NULL"
    games = _run_query(query, [], config.db_url)
    return games

def fetch_online_wfc_games(gamespy_id=None):
    try:
        resp = requests.get(WFC_STATS_API, timeout=10)
        resp.raise_for_status()
        stats = resp.json()
    except Exception as e:
        print(f"Error fetching WFC stats: {e}")
        return {}
    
    wfc_compatible_games = fetch_wfc_games()
    
    # Optionally filter by gamespy_id if provided
    if gamespy_id:
        wfc_compatible_games = [game for game in wfc_compatible_games if game.get("gamespy_id") == gamespy_id]

    merged_games = []
    for game in wfc_compatible_games:
        gid = game.get("gamespy_id")
        if gid and gid in stats:
            stat = stats[gid]
            merged = dict(game)
            merged["players_online"] = stat.get("online", 0)
            merged["active"] = stat.get("active", 0)
            merged["groups"] = stat.get("groups", 0)
            merged_games.append(merged)

    return merged_games

def find_user_by_wii_number(wii_number, attempt=0):
    base_url = config.authentik_api_url.rstrip("/")
    url = f'{base_url}/core/users/?page_size=30&attributes=%7B%22wiis__{attempt}__wii_number%22%3A+"{wii_number}"%7D'
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.authentik_service_account_token}",
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if (
            not results and attempt < 10
        ):  # Honestly fuck you if you have more than 9 Wiis.
            return find_user_by_wii_number(wii_number, attempt=attempt + 1)
        return results[0] if results else None
    except requests.RequestException as e:
        print(f"Authentik API error: {e}")
        return None


def fetch_authentik_users():
    base_url = config.authentik_api_url.rstrip("/")
    url = f"{base_url}/core/users/?page_size=30&attributes=%7B%22public_profile%22%3A+true%7D"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.authentik_service_account_token}",
    }

    users = []

    try:
        while url:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            users.extend(data.get("results", []))
            next_url = data.get("pagination", {}).get("next")

            if isinstance(next_url, str) and (
                next_url.startswith("http://") or next_url.startswith("https://")
            ):
                url = next_url
            else:
                url = None

    except requests.RequestException as e:
        print(f"Authentik API error: {e}")
        return []

    return users


def search_authentik_users_by_name(search_query):
    if not search_query or not search_query.strip():
        return []

    base_url = config.authentik_api_url.rstrip("/")
    # Use search parameter for username search
    url = f"{base_url}/core/users/?page_size=50&search={search_query}&attributes=%7B%22public_profile%22%3A+true%7D"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.authentik_service_account_token}",
    }

    users = []
    try:
        while url:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            users.extend(
                [user for user in results if user.get("attributes", {}).get("wiis")]
            )
            next_url = data.get("pagination", {}).get("next")
            if isinstance(next_url, str) and (
                next_url.startswith("http://") or next_url.startswith("https://")
            ):
                url = next_url
            else:
                url = None

    except requests.RequestException as e:
        print(f"Authentik API error searching for '{search_query}': {e}")
        return []

    return users


def normalize_serial(serial):
    return serial.strip("[]'\" ").replace("-", "") if serial else serial


def extract_serial_prefix(serial):
    return [serial[:12]]


def generate_gravatar_url(email):
    if not email:
        return "https://www.gravatar.com/avatar/default?d=identicon&s=128"
    hash_digest = hashlib.sha256(email.encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_digest}?d=identicon&s=128"


def build_viewed_user_info(authentik_user):
    if isinstance(authentik_user, list):
        authentik_user = authentik_user[0] if authentik_user else {}

    username = authentik_user.get("username")
    email = authentik_user.get("email", "")
    picture_url = generate_gravatar_url(email)

    wiis = authentik_user.get("attributes", {}).get("wiis") or authentik_user.get(
        "wiis", []
    )
    wii_numbers = []

    if isinstance(wiis, list):
        for wii in wiis:
            if isinstance(wii, dict):
                wii_number = wii.get("wii_number")
                if wii_number:
                    wii_numbers.append(wii_number)
    return {
        "username": username,
        "profile_picture": picture_url,
        "linked_wii_no": wii_numbers,
        "serial_number": wii_numbers,
    }


def build_unclaimed_user_info(serial, logged_in_user_picture):
    return {
        "username": serial,
        "profile_picture": logged_in_user_picture,
        "linked_wii_no": [serial],
        "serial_number": serial,
    }


def format_serial(s):
    s = str(s)
    return "-".join([s[i : i + 4] for i in range(0, len(s), 4)])


def format_playtime(minutes):
    if not minutes:
        return "0m"
    minutes = int(minutes)
    years = minutes // (365 * 24 * 60)
    remaining = minutes % (365 * 24 * 60)
    days = remaining // (24 * 60)
    remaining = remaining % (24 * 60)
    hours = remaining // 60
    mins = remaining % 60

    parts = []
    if years > 0:
        parts.append(f"{years}y")
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if mins > 0 or not parts:
        parts.append(f"{mins}m")
    return " ".join(parts)
