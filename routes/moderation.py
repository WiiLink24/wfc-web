import json
import os

from psycopg2.extras import Json
import config
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    g,
    session,
    abort,
)
from functools import wraps

from routes.auth import get_logged_in_user_info
from utils.utils import _run_query, _run_query_one, _execute

MODERATOR_GROUP_UUID = getattr(config, "moderator_group_uuid", "")

PATCHES_DB_URL = getattr(config, "wfc_patches_db_url", None)
PATCHES_STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "static", "patches"
)


def moderator_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        userData = get_logged_in_user_info()
        if not userData:
            abort(401)
        user_groups = userData["groups"]
        if MODERATOR_GROUP_UUID not in user_groups:
            abort(403)
        return f(*args, **kwargs)

    return decorated


moderation_bp = Blueprint("moderation", __name__, url_prefix="/moderation")


def _normalize_observations(observations):
    if not observations:
        return []
    if isinstance(observations, list):
        return observations
    if isinstance(observations, str):
        try:
            parsed = json.loads(observations)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def _normalize_patch_ids(patch_ids):
    if not patch_ids:
        return []
    if isinstance(patch_ids, list):
        return patch_ids
    if isinstance(patch_ids, str):
        try:
            parsed = json.loads(patch_ids)
            return parsed if isinstance(parsed, list) else []
        except (ValueError, TypeError):
            return []
    return []


def search_titles(query_text="", limit=100):
    clean_query = (query_text or "").strip()
    params = []

    query = """
        SELECT
            game_id,
            gamespy_id,
            title_en,
            release_year,
            game_type,
            region,
            is_supported,
            is_featured,
            wfc_observations
        FROM titles
    """

    if clean_query:
        query += """
            WHERE
                title_en ILIKE %s
                OR gamespy_id ILIKE %s
                OR CAST(game_id AS TEXT) ILIKE %s
        """
        like = f"%{clean_query}%"
        params.extend([like, like, like])

    query += """
        ORDER BY title_en ASC
        LIMIT %s
    """
    params.append(limit)

    return _run_query(query, params)


def get_patches_for_game(gamespy_id):
    if not PATCHES_DB_URL:
        return None
    row = _run_query_one(
        "SELECT gamename, patchid, gameid FROM pages WHERE gamespyid = %s",
        [gamespy_id],
        PATCHES_DB_URL,
    )
    if not row:
        return None
    return {
        "gamename": row["gamename"],
        "patch_ids": _normalize_patch_ids(row["patchid"]),
        "gameid": row["gameid"],
    }


def upsert_patches(gamespy_id, gamename, gameid, patch_ids):
    if not PATCHES_DB_URL:
        return False
    try:
        updated = _execute(
            "UPDATE pages SET gamename = %s, gameid = %s, patchid = %s WHERE gamespyid = %s",
            [gamename, gameid, Json(patch_ids), gamespy_id],
            PATCHES_DB_URL,
        )
        if updated == 0:
            _execute(
                "INSERT INTO pages (gamespyid, gamename, gameid, patchid) VALUES (%s, %s, %s, %s)",
                [gamespy_id, gamename, gameid, Json(patch_ids)],
                PATCHES_DB_URL,
            )
        return True
    except Exception:
        return False


def delete_patches_for_game(gamespy_id):
    if not PATCHES_DB_URL:
        return False
    try:
        _execute("DELETE FROM pages WHERE gamespyid = %s", [gamespy_id], PATCHES_DB_URL)
        return True
    except Exception:
        return False


def update_title_support_and_observations(
    game_id, is_supported, observation=None, new_gamespy_id=None, is_featured=False
):
    if not game_id:
        return False

    row = _run_query_one(
        "SELECT wfc_observations FROM titles WHERE game_id = %s",
        [game_id],
    )
    if not row:
        return False

    observations = _normalize_observations(row["wfc_observations"])
    if observation:
        observations.append(observation)

    if new_gamespy_id:
        query = """
            UPDATE titles
            SET gamespy_id = %s,
                is_supported = %s,
                is_featured = %s,
                wfc_observations = %s
            WHERE game_id = %s
        """
        params = [
            new_gamespy_id,
            is_supported,
            is_featured,
            Json(observations),
            game_id,
        ]
    else:
        query = """
            UPDATE titles
            SET is_supported = %s,
                is_featured = %s,
                wfc_observations = %s
            WHERE game_id = %s
        """
        params = [is_supported, is_featured, Json(observations), game_id]

    try:
        return _execute(query, params) > 0
    except Exception:
        return False


@moderation_bp.route("/titles", methods=["GET", "POST"])
@moderator_required
def titles_panel():
    """Moderation panel for title support and observations."""
    if not getattr(g, "oidc_user", None) or not g.oidc_user.logged_in:
        flash("Please log in to access the moderation panel.")
        return redirect(url_for("auth_routes.login"))

    if request.method == "POST":
        game_id = (request.form.get("game_id") or "").strip()
        gamespy_id = (request.form.get("gamespy_id") or "").strip()
        new_gamespy_id = (request.form.get("new_gamespy_id") or "").strip()
        query_text = (request.form.get("q") or "").strip()

        try:
            is_supported = int(request.form.get("is_supported", "0"))
        except ValueError:
            is_supported = 0
        is_featured = request.form.get("is_featured") == "on"

        obs_title = (request.form.get("obs_title") or "").strip()
        obs_description = (request.form.get("obs_description") or "").strip()
        obs_icon = (request.form.get("obs_icon") or "info").strip() or "info"

        observation = None
        if obs_title and obs_description:
            observation = {
                "title": obs_title,
                "description": obs_description,
                "icon": obs_icon,
            }

        if not game_id:
            flash("Missing title identifier.")
            return redirect(url_for("moderation.titles_panel", q=query_text))

        updated = update_title_support_and_observations(
            game_id=game_id,
            is_supported=is_supported,
            observation=observation,
            new_gamespy_id=new_gamespy_id,
            is_featured=is_featured,
        )

        source_identifier = gamespy_id or game_id
        target_identifier = new_gamespy_id or gamespy_id or game_id

        if updated:
            if target_identifier != source_identifier:
                flash(f"Updated {source_identifier} to {target_identifier}.")
            else:
                flash(f"Updated {source_identifier}.")
        else:
            flash(f"Could not update {source_identifier}.")

        return redirect(url_for("moderation.titles_panel", q=query_text))

    query_text = (request.args.get("q") or "").strip()
    titles = search_titles(query_text=query_text, limit=150) if query_text else []
    user_info = get_logged_in_user_info()

    return render_template(
        "pages/moderation_titles.html",
        user_info=user_info,
        query_text=query_text,
        titles=titles,
    )


@moderation_bp.route("/<game_id>", methods=["GET", "POST"])
@moderator_required
def moderation_edit(game_id):
    """Edit a title by Game ID (string or int)."""
    if not getattr(g, "oidc_user", None) or not g.oidc_user.logged_in:
        flash("Please log in to access the moderation panel.")
        return redirect(url_for("auth_routes.login"))

    title = _run_query_one("SELECT * FROM titles WHERE game_id = %s", [game_id])
    if not title:
        flash("Title not found.")
        return redirect(url_for("moderation.titles_panel"))
    title["wfc_observations"] = _normalize_observations(title.get("wfc_observations"))

    patches = get_patches_for_game(title.get("gamespy_id") or "") or {
        "patch_ids": [],
        "gameid": "",
        "gamename": title.get("title_en", ""),
    }

    if request.method == "POST":
        action = request.form.get("patch_action", "").strip()
        gamespy_id = title.get("gamespy_id", "").strip()

        # Handle patches actions
        if action == "add_patch":
            patch_id = (request.form.get("new_patch_id") or "").strip().upper()
            patch_file = request.files.get("patch_file")
            if not patch_id:
                flash("Patch ID is required.")
                return redirect(url_for("moderation.moderation_edit", game_id=game_id))

            patch_ids = list(patches.get("patch_ids", []))
            if patch_id not in patch_ids:
                patch_ids.append(patch_id)
                patch_ids.sort()

            gameid = (
                (request.form.get("patch_gameid") or patches.get("gameid") or "")
                .strip()
                .upper()
            )
            gamename = (
                request.form.get("patch_gamename")
                or patches.get("gamename")
                or title.get("title_en", "")
            ).strip()

            if upsert_patches(gamespy_id, gamename, gameid, patch_ids):
                if patch_file and patch_file.filename:
                    try:
                        os.makedirs(PATCHES_STATIC_DIR, exist_ok=True)
                        filepath = os.path.join(PATCHES_STATIC_DIR, f"{patch_id}.txt")
                        patch_file.save(filepath)
                        flash(f"Patch {patch_id} added and file saved.")
                    except Exception as e:
                        flash(f"Patch saved to DB but file upload failed: {e}")
                else:
                    flash(f"Patch {patch_id} added.")
            else:
                flash("Failed to add patch.")
            return redirect(url_for("moderation.moderation_edit", game_id=game_id))

        elif action == "remove_patch":
            patch_id = (request.form.get("remove_patch_id") or "").strip().upper()
            patch_ids = [p for p in patches.get("patch_ids", []) if p != patch_id]
            gameid = patches.get("gameid", "")
            gamename = patches.get("gamename", title.get("title_en", ""))

            if not patch_ids:
                delete_patches_for_game(gamespy_id)
                flash(f"Patch {patch_id} removed. No patches left, entry deleted.")
            else:
                if upsert_patches(gamespy_id, gamename, gameid, patch_ids):
                    flash(f"Patch {patch_id} removed.")
                else:
                    flash("Failed to remove patch.")
            return redirect(url_for("moderation.moderation_edit", game_id=game_id))

        # Handle title edits
        new_gamespy_id = request.form.get("gamespy_id", "").strip()
        is_supported = int(
            request.form.get("is_supported", title.get("is_supported", 0))
        )
        is_featured = "1" in request.form.getlist("is_featured")

        if "remove_obs" in request.form:
            observations = []
        else:
            obs_title = request.form.get("obs_title", "").strip()
            obs_description = request.form.get("obs_description", "").strip()
            obs_icon = request.form.get("obs_icon", "info").strip() or "info"
            if obs_title and obs_description:
                observations = [
                    {
                        "title": obs_title,
                        "description": obs_description,
                        "icon": obs_icon,
                    }
                ]
            else:
                observations = []

        try:
            _execute(
                """
                UPDATE titles
                SET gamespy_id = %s,
                    is_supported = %s,
                    is_featured = %s,
                    wfc_observations = %s
                WHERE game_id = %s
                """,
                [
                    new_gamespy_id,
                    is_supported,
                    is_featured,
                    Json(observations),
                    game_id,
                ],
            )
            flash("Game updated successfully.")
        except Exception as e:
            flash(f"Error updating game: {e}")
        return redirect(url_for("moderation.moderation_edit", game_id=game_id))

    # List existing patch files in static/patches for UI indicators
    try:
        existing_patch_files = (
            set(os.listdir(PATCHES_STATIC_DIR))
            if os.path.isdir(PATCHES_STATIC_DIR)
            else set()
        )
    except Exception:
        existing_patch_files = set()

    user_info = get_logged_in_user_info()
    return render_template(
        "pages/moderation_edit.html",
        user_info=user_info,
        title=title,
        patches=patches,
        existing_patch_files=existing_patch_files,
    )
