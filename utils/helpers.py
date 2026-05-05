from flask import current_app


def get_oidc():
    return current_app.extensions.get("oidc")


def parse_int(value):
    """Parse string to int, return None if invalid"""
    return int(value) if value.isdigit() else None


def parse_fc(fc):
    return fc.replace("-", "") if fc else None


def is_public_profile(user_profile, logged_in_user):
    if logged_in_user and user_profile.get("username") == logged_in_user.get(
        "username"
    ):
        return True
    public_profile = user_profile.get("attributes", {}).get("public_profile")
    return public_profile if public_profile is not None else False


def get_online_totals(online_stats):
    totals = {"online": 0, "active": 0, "groups": 0}
    for stat in online_stats:
        totals["online"] += stat.get("players_online", 0)
        totals["active"] += stat.get("active", 0)
        totals["groups"] += stat.get("groups", 0)
        totals["games"] = len(online_stats)
    return totals


def get_special_template_for_game(gamespy_id):
    special_templates = {
        "mariokartwii": "groups-mariokartwii.html",
        "smashbrosxwii": "groups-smashbrosxwii.html",
    }
    return special_templates.get(gamespy_id)
