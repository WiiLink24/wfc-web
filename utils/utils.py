import psycopg2
import config
import requests
import hashlib

WFC_STATS_API = getattr(config, "wfc_stats_api", "")
WFC_GROUPS_API = getattr(config, "wfc_groups_api", "")
BAN_INFO_API = getattr(config, "ban_info_api", "")

def fetch_ban_info(query):
    try:
        resp = requests.get(BAN_INFO_API.format(query=query), timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Error fetching ban info: {e}")
        return {"error": query, "found": 0, "infolist": []}

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


def generate_gravatar_url(email):
    if not email:
        return "https://www.gravatar.com/avatar/default?d=identicon&s=128"
    hash_digest = hashlib.sha256(email.encode()).hexdigest()
    return f"https://www.gravatar.com/avatar/{hash_digest}?d=identicon&s=128"

def get_compat_totals():
    query_full = "SELECT COUNT(*) as total FROM titles WHERE is_supported = 2"
    query_partial = "SELECT COUNT(*) as total FROM titles WHERE is_supported = 1"
    result_full = _run_query(query_full, [], config.db_url)
    result_partial = _run_query(query_partial, [], config.db_url)
    return {
        "full": result_full[0]["total"] if result_full else 0,
        "partial": result_partial[0]["total"] if result_partial else 0
    }

def get_groups_for_game(game_name):
    try:
        resp = requests.get(WFC_GROUPS_API, timeout=10)
        resp.raise_for_status()
        groups = resp.json()        
        for g in groups:
            if "created" in g and g["created"]:
                try:
                    dt = g["created"].replace("T", " ").replace("Z", "")
                    if "." in dt:
                        dt = dt.split(".")[0]
                    g["created"] = dt
                except Exception:
                    pass
        
        return [g for g in groups if g.get("game") == game_name]
    except Exception as e:
        print(f"Error fetching WFC groups: {e}")
        return []