from flask import Blueprint, redirect, url_for
from utils.utils import generate_gravatar_url

auth_routes_bp = Blueprint("auth_routes", __name__)

_oidc = None


def set_oidc(oidc):
    global _oidc
    _oidc = oidc


def get_logged_in_user_info():
    """Get logged in user info from OIDC and format for templates."""
    if not (_oidc and _oidc.user_loggedin):
        return None
    
    user_data = _oidc.user_getinfo([
        "preferred_username", "email", "name", "given_name"
    ])
    
    print("OIDC user data:", user_data)  # Debugging output
    
    if not user_data:
        return None
    
    # Transform OIDC data to template format
    return {
        "username": user_data.get("preferred_username", ""),
        "full_name": user_data.get("name", ""),
        "email": user_data.get("email", ""),
        "profile_picture": generate_gravatar_url(user_data.get("email", "")),
        "groups": user_data.get("groups", []),
    }


@auth_routes_bp.route("/login")
def login():
    """OIDC login route."""
    if _oidc:
        return _oidc.oidc_auth("public_routes.index")
    return redirect(url_for("public_routes.index"))


@auth_routes_bp.route("/logout")
def logout():
    """OIDC logout route."""
    _oidc.oidc_logout()
    return redirect(url_for("public_routes.index"))
