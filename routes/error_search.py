import requests
from flask import Blueprint, request, jsonify, render_template
error_search_bp = Blueprint("error_search", __name__, url_prefix="/error-search")

@error_search_bp.route("/api", methods=["GET"])
def api():
    code = request.args.get("code", "")
    if not code:
        return jsonify([{"error": code, "found": 0, "infolist": []}])
    try:
        resp = requests.get(f"https://wfc-error.wiilink.ca/error?code={code}", timeout=3)
        if resp.status_code == 200:
            return resp.content, resp.status_code, {'Content-Type': 'application/json'}
        else:
            return jsonify([{"error": code, "found": 0, "infolist": []}])
    except Exception:
        return jsonify([{"error": code, "found": 0, "infolist": []}])

@error_search_bp.route("/", methods=["GET"])
def search_page():
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
