import os
from flask import Flask, render_template, g
from flask_oidc import OpenIDConnect
from flask_session import Session

import config
from routes.public import public_routes_bp
from routes.auth import auth_routes_bp, set_oidc, get_logged_in_user_info
from routes.misc import misc_routes_bp
from routes.pages import pages_bp
from routes.moderation import moderation_bp
from routes.error_search import error_search_bp
from routes.dummy import dummy_bp

app = Flask(__name__)
app.config["SECRET_KEY"] = config.secret_key
app.config["OIDC_CLIENT_SECRETS"] = config.oidc_client_secrets_json
app.config["OIDC_SCOPES"] = "openid profile email"
app.config["OIDC_OVERWRITE_REDIRECT_URI"] = config.oidc_redirect_uri
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = os.getenv(
    "SESSION_FILE_DIR", os.path.join(os.path.dirname(__file__), "session")
)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True

os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)

oidc = OpenIDConnect(app)
Session(app)


# Set OIDC instance for blueprints
set_oidc(oidc)

# Register dummy API blueprint
app.register_blueprint(dummy_bp)



# Inject user_info into all templates
@app.context_processor
def inject_user_info():
    return {'user_info': get_logged_in_user_info()}


# Register blueprints
app.register_blueprint(public_routes_bp)
app.register_blueprint(auth_routes_bp)
app.register_blueprint(misc_routes_bp)
app.register_blueprint(pages_bp)
app.register_blueprint(moderation_bp)

# Register error search blueprint
app.register_blueprint(error_search_bp)


# Global error handlers
@app.errorhandler(404)
def handle_404(error):
    """Handle 404 Not Found errors"""
    return (
        render_template(
            "errors/error.html",
            error_code=404,
            error_title="Page Not Found",
            error_message="The page you're looking for doesn't exist.",
        ),
        404,
    )


@app.errorhandler(500)
def handle_500(error):
    """Handle 500 Internal Server errors"""
    return (
        render_template(
            "errors/error.html",
            error_code=500,
            error_title="Internal Server Error",
            error_message="Something went wrong on our end.",
        ),
        500,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

