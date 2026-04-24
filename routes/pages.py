from flask import Blueprint, render_template

pages_bp = Blueprint("pages", __name__)



@pages_bp.route("/rules")
def rules():
    """WiiLink WFC Rules page."""
    return render_template("pages/rules.html")


@pages_bp.route("/online")
def online():
    """List of all online games."""
    return render_template("pages/online.html")


from utils.utils import fetch_wfc_game_data

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
