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

    response = {
        "pid": 123456789,
        "fc": "5261793740959345",
        "name": "TestUser",
        "reason": "Violation of rules",
        "tos": True,
        "issued": datetime.utcnow().isoformat() + "Z",
        "expires": (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z",
    }

    if q:
        if q.isdigit() and int(q) == response["pid"]:
            return jsonify(response)
        elif q == response["fc"]:
            return jsonify(response)
        else:
            return jsonify({"error": "ban not found"}), 404
    return jsonify(response)


@dummy_bp.route("/api/dummy_groups", methods=["GET"])
def dummy_game_groups():

    groups_data = [
        {
            "id": "TXMXUO",
            "game": "mariokartwii",
            "type": "anybody",
            "suspend": False,
            "host": "0",
            "rk": "vs",
            "players": [
                {
                    "count": "2",
                    "pid": "124",
                    "name": "w",
                    "fc": "4252-0176-2428",
                    "ev": "5524",
                    "eb": "5075",
                    "mii": [
                        {
                            "mii": "a900003f0000000000000000000000000000000000007f2d873569b6000000000004784031bd28a2088c08401449b88d108a008a250400000000000000000000000000000000000000003faa",
                            "name": "w",
                        },
                        {
                            "mii": "a900003f0000000000000000000000000000000000007f2d873569b6000000000004784031bd28a2088c08401449b88d108a008a250400000000000000000000000000000000000000003faa",
                            "name": "Player",
                        },
                    ],
                },
                {
                    "count": "1",
                    "pid": "122",
                    "name": "no name",
                    "fc": "2233-3829-9514",
                    "ev": "4912",
                    "eb": "5000",
                    "mii": [
                        {
                            "mii": "a900003f0000000000000000000000000000000000007f2d873569b6000000000004784031bd28a2088c08401449b88d108a008a250400000000000000000000000000000000000000003faa",
                            "name": "Player",
                        }
                    ],
                },
            ],
        },
        {
            "id": "LFDKIG",
            "game": "puyopuyo7ds",
            "created": "2024-04-21T18:40:18.753262799Z",
            "type": "anybody",
            "suspend": True,
            "host": "0",
            "players": [
                {
                    "count": "",
                    "pid": "1000001465",
                    "name": "mkwcat",
                    "conn_map": "22",
                    "conn_fail": "0",
                    "suspend": "",
                    "fc": "4262-0176-3769",
                },
                {
                    "count": "",
                    "pid": "1000001464",
                    "name": "ICAtrevor",
                    "conn_map": "22",
                    "conn_fail": "0",
                    "suspend": "",
                    "fc": "4820-3633-8616",
                },
                {
                    "count": "",
                    "pid": "1000001466",
                    "name": "alejandro1",
                    "conn_map": "22",
                    "conn_fail": "0",
                    "suspend": "",
                    "fc": "3703-6718-8922",
                },
            ],
        },
    ]

    return jsonify(groups_data)
