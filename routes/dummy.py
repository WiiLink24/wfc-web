import random
from flask import Blueprint, jsonify

dummy_bp = Blueprint("dummy", __name__)

def random_gameplay_stats():
    return {
        "online": random.randint(0, 10),
        "groups": random.randint(0, 5),
        "active": random.randint(0, 10),
    }

@dummy_bp.route("/api/dummy_stats")
def dummy_stats():
    games = ["mariokartwii", "smashbrosxwii", "tetrisds", "animalcrossingwii"]
    data = {gid: random_gameplay_stats() for gid in games}
    data["global"] = {
        "online": sum(d["online"] for d in data.values()),
        "active": sum(d["active"] for d in data.values()),
        "groups": sum(d["groups"] for d in data.values()),
    }
    return jsonify(data)
