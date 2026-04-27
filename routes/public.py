from flask import Blueprint, render_template
from utils.utils import fetch_featured_wfc_games, fetch_online_wfc_games
from routes.auth import get_logged_in_user_info

public_routes_bp = Blueprint("public_routes", __name__)


@public_routes_bp.route("/")
def index():
    """Main page showing featured games."""
    featured_games = fetch_featured_wfc_games()
    online_stats = fetch_online_wfc_games()
    user_info = get_logged_in_user_info()
    return render_template(
        "index.html",
        featured_games=featured_games,
        online_stats=online_stats,
        user_info=user_info,
    )
