from flask import Blueprint, render_template, request, redirect, url_for
import requests
from utils.utils import (
    fetch_ban_info,
    fetch_wfc_game_data,
    fetch_ban_info,
    find_user_by_wii_number,
    fetch_online_wfc_games,
    fetch_featured_wfc_games,
    fetch_wfc_games,
    get_compat_totals,
    get_groups_for_game,
    fetch_patches_for_game,
)
from utils.helpers import (
    is_public_profile,
    parse_fc,
    get_online_totals,
    get_special_template_for_game,
)
from routes.auth import get_logged_in_user_info

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    """Main page showing featured games."""
    featured_games = fetch_featured_wfc_games()
    online_stats = fetch_online_wfc_games()
    user_info = get_logged_in_user_info()
    online_totals = get_online_totals(online_stats)
    compat_totals = get_compat_totals()
    return render_template(
        "index.html",
        featured_games=featured_games,
        online_stats=online_stats,
        user_info=user_info,
        online_totals=online_totals,
        compat_totals=compat_totals,
    )


@pages_bp.route("/search", methods=["GET"])
def search():
    query = request.args.get("q", "").strip().lower()
    results = []
    if query:
        for game in fetch_wfc_games():
            if (
                query in game.get("title_en", "").lower()
                or query in (game.get("gamespy_id") or "").lower()
            ):
                results.append(game)
    return render_template("search_results.html", query=query, results=results)


@pages_bp.route("/ban-search", methods=["GET"])
def ban_search():
    code = request.args.get("q", "")
    logged_in_user = get_logged_in_user_info()
    user_data = None
    from routes.auth import _oidc

    if _oidc and _oidc.user_loggedin:
        user_data = _oidc.user_getinfo(
            [
                "sub",
                "email",
                "email_verified",
                "name",
                "given_name",
                "preferred_username",
                "nickname",
                "groups",
                "wiis",
                "public_profile",
                "nonce",
            ]
        )

    if code:
        ban_info = fetch_ban_info(parse_fc(code))
        user_found = (
            find_user_by_wii_number(parse_fc(ban_info.get("fc", "")))
            if ban_info
            else None
        )

        if not user_found:
            return render_template(
                "errors/baninfo_search.html",
                fc=code,
                result=ban_info,
                user_data=user_data,
            )

        if is_public_profile(user_found, logged_in_user):
            return render_template(
                "errors/baninfo_search.html",
                fc=code,
                result=ban_info,
                user_data=user_data,
            )
        else:
            return render_template(
                "errors/baninfo_search.html",
                fc=code,
                result={"error": "not_public"},
                user_data=user_data,
            )

    return render_template("errors/baninfo_search.html", user_data=user_data)


@pages_bp.route("/error-search", methods=["GET"])
def error_search():
    code = request.args.get("code", "")
    result = None
    if code:
        try:
            resp = requests.get(
                f"https://wfc-error.wiilink.ca/error?code={code}", timeout=3
            )
            if resp.status_code == 200:
                result = resp.json()[0]
            else:
                result = {"error": code, "found": 0, "infolist": []}
        except Exception:
            result = {"error": code, "found": 0, "infolist": []}
    return render_template("errors/error_search.html", code=code, result=result)


@pages_bp.route("/rules")
def rules():
    return render_template("pages/rules.html")


@pages_bp.route("/online")
def online():
    return redirect(url_for("pages.index"), code=302)


@pages_bp.route("/online/<gamespy_id>")
def online_game(gamespy_id):
    game = fetch_wfc_game_data(gamespy_id)
    live_stats = None
    stats_list = fetch_online_wfc_games(gamespy_id)
    groups_data = get_groups_for_game(gamespy_id)
    special_template = get_special_template_for_game(gamespy_id)
    patches = fetch_patches_for_game(gamespy_id)
    if stats_list:
        live_stats = stats_list[0]
    if not game:
        return (
            render_template(
                "errors/error.html",
                error_code=404,
                error_title="Game Not Found",
                error_message="No game found for this ID.",
                error_details="",
            ),
            404,
        )
    return render_template(
        "pages/online-game.html",
        game=game,
        live_stats=live_stats,
        groups_data=groups_data,
        special_template=special_template,
        patches=patches,
    )


@pages_bp.route("/api/online/<gamespy_id>")
def api_online_game(gamespy_id):
    stats_list = fetch_online_wfc_games(gamespy_id)
    if stats_list:
        return {stats_list[0]}
    return {None}


@pages_bp.route("/online/<game_name>/<room_name>")
def online_room(game_name, room_name):
    """Specific room details."""
    return render_template(
        "pages/online-room.html", game_name=game_name, room_name=room_name
    )


@pages_bp.route("/guide")
def guide():
    return render_template("pages/guide.html")


@pages_bp.route("/guide/dolphin")
def guide_dolphin():
    return render_template("pages/guide-dolphin.html")


@pages_bp.route("/dolphin")
def dolphin():
    return render_template("pages/guide-dolphin.html")


@pages_bp.route("/launcher")
def launcher():
    return render_template("pages/launcher.html")


@pages_bp.route("/dns")
def dns():
    return render_template("pages/dns.html")


@pages_bp.route("/payload")
def payload():
    return render_template("pages/payload.html")
