from flask import Blueprint, redirect, url_for, request, render_template
from utils.utils import fetch_wfc_games

misc_routes_bp = Blueprint("misc_routes", __name__)

@misc_routes_bp.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip().lower()
    results = []
    if query:
        for game in fetch_wfc_games():
            if query in game.get("title_en", "").lower() or query in (game.get("gamespy_id") or "").lower():
                results.append(game)
    return render_template("search_results.html", query=query, results=results)


@misc_routes_bp.route("/logout")
def logout():
    """Logout route - redirect to auth logout."""
    return redirect(url_for("auth_routes.logout"))
