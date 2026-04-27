from flask import Blueprint, render_template, request
import requests
from utils.utils import fetch_ban_info, fetch_wfc_game_data, fetch_ban_info, find_user_by_wii_number
from utils.helpers import is_public_profile, parse_fc
from routes.auth import get_logged_in_user_info
from routes.auth import _oidc

pages_bp = Blueprint("pages", __name__)

@pages_bp.route("/ban-search", methods=["GET"])
def ban_search():
    code = request.args.get("q", "")
    logged_in_user = get_logged_in_user_info()
    user_data = None
    if _oidc and _oidc.user_loggedin:
        user_data = _oidc.user_getinfo([
            "sub", "email", "email_verified", "name", "given_name", "preferred_username", "nickname", "groups", "wiis", "public_profile", "nonce"
        ])
    
    if code:
        ban_info = fetch_ban_info(parse_fc(code))
        user_found = find_user_by_wii_number(parse_fc(ban_info.get("fc", ""))) if ban_info else None
        
        if not user_found:
            return render_template("errors/baninfo_search.html", fc=code, result=ban_info, user_data=user_data)
        
        if is_public_profile(user_found, logged_in_user):
            return render_template("errors/baninfo_search.html", fc=code, result=ban_info, user_data=user_data)
        else:
            return render_template("errors/baninfo_search.html", fc=code, result={"error": "not_public"}, user_data=user_data)
    
    return render_template("errors/baninfo_search.html", user_data=user_data)

@pages_bp.route("/error-search", methods=["GET"])
def error_search():
    code = request.args.get("code", "")
    result = None
    if code:
        try:
            resp = requests.get(f"https://wfc-error.wiilink.ca/error?code={code}", timeout=3)
            if resp.status_code == 200:
                result = resp.json()[0]
            else:
                result = {"error": code, "found": 0, "infolist": []}
        except Exception:
            result = {"error": code, "found": 0, "infolist": []}
    return render_template("errors/error_search.html", code=code, result=result)


@pages_bp.route("/rules")
def rules():
    """WiiLink WFC Rules page."""
    return render_template("pages/rules.html")


@pages_bp.route("/online")
def online():
    """List of all online games."""
    return render_template("pages/online.html")


@pages_bp.route("/online/<gamespy_id>")
def online_game(gamespy_id):
    """Game-specific info and rooms."""
    game = fetch_wfc_game_data(gamespy_id)
    if not game:
        return render_template("errors/error.html", error_code=404, error_title="Game Not Found", error_message="No game found for this ID.", error_details=""), 404
    return render_template("pages/online-game.html", game=game)


@pages_bp.route("/online/<game_name>/<room_name>")
def online_room(game_name, room_name):
    """Specific room details."""
    return render_template("pages/online-room.html", game_name=game_name, room_name=room_name)


@pages_bp.route("/guide")
def guide():
    """Installation and patching guide."""
    return render_template("pages/guide.html")


@pages_bp.route("/guide/dolphin")
def guide_dolphin():
    """Dolphin-specific setup guide."""
    return render_template("pages/guide-dolphin.html")


@pages_bp.route("/dolphin")
def dolphin():
    """Dolphin setup (redirects to /guide/dolphin)."""
    return render_template("pages/guide-dolphin.html")


@pages_bp.route("/launcher")
def launcher():
    """WiiLink WFC Launcher information."""
    return render_template("pages/launcher.html")


@pages_bp.route("/dns")
def dns():
    """DNS Server information."""
    return render_template("pages/dns.html")


@pages_bp.route("/payload")
def payload():
    """Payload information."""
    return render_template("pages/payload.html")
