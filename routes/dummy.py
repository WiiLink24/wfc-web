import random
from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta

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

@dummy_bp.route("/api/dummy/baninfo", methods=["GET"])
def dummy_baninfo():
    q = request.args.get("q", "")
    print(f"Received baninfo request with q={q}")
    """
    Dummy endpoint for ban info. Returns a static example response.
    """
    response = {
        "pid": 123456789,
        "fc": "5261793740959345",
        "name": "TestUser",
        "reason": "Violation of rules",
        "tos": True,
        "issued": datetime.utcnow().isoformat() + 'Z',
        "expires": (datetime.utcnow() + timedelta(days=7)).isoformat() + 'Z'
    }
    
    if q:
        if q.isdigit() and int(q) == response["pid"]:
            return jsonify(response)
        elif q == response["fc"]:
            return jsonify(response)
        else:
            return jsonify({"error": "ban not found"}), 404
    return jsonify(response)
