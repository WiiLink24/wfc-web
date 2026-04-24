import json

import psycopg2
from psycopg2.extras import Json
import config
from flask import Blueprint, render_template, request, redirect, url_for, flash, g

from routes.auth import get_logged_in_user_info

moderation_bp = Blueprint("moderation", __name__, url_prefix="/moderation")


def search_titles(query_text="", limit=100):
    """Search titles by name or GameSpy ID for moderation."""
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

    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        cur.execute(query, params)
        rows = cur.fetchall()
        columns = [desc[0] for desc in cur.description]
        return [dict(zip(columns, row)) for row in rows]
    finally:
        cur.close()
        conn.close()


def _normalize_observations(observations):
    """Normalize JSONB observations into a list of dicts."""
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


def update_title_support_and_observations(game_id, is_supported, observation=None, new_gamespy_id=None, is_featured=False):
    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        if not game_id:
            return False

        cur.execute(
            "SELECT wfc_observations FROM titles WHERE game_id = %s",
            [game_id],
        )
        row = cur.fetchone()
        if not row:
            return False

        observations = _normalize_observations(row[0])
        if observation:
            observations.append(observation)

        if new_gamespy_id:
            cur.execute(
                """
                UPDATE titles
                SET
                    gamespy_id = %s,
                    is_supported = %s,
                    is_featured = %s,
                    wfc_observations = %s
                WHERE game_id = %s
                """,
                [new_gamespy_id, is_supported, is_featured, Json(observations), game_id],
            )
        else:
            cur.execute(
                """
                UPDATE titles
                SET
                    is_supported = %s,
                    is_featured = %s,
                    wfc_observations = %s
                WHERE game_id = %s
                """,
                [is_supported, is_featured, Json(observations), game_id],
            )

        conn.commit()
        return cur.rowcount > 0
    except psycopg2.Error:
        conn.rollback()
        return False
    finally:
        cur.close()
        conn.close()


@moderation_bp.route("/titles", methods=["GET", "POST"])
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
def moderation_edit(game_id):
    """Edit a title by Game ID (string or int)."""
    if not getattr(g, "oidc_user", None) or not g.oidc_user.logged_in:
        flash("Please log in to access the moderation panel.")
        return redirect(url_for("auth_routes.login"))

    conn = psycopg2.connect(config.db_url)
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM titles WHERE game_id = %s", [game_id])
        row = cur.fetchone()
        if not row:
            flash("Title not found.")
            return redirect(url_for("moderation.titles_panel"))
        columns = [desc[0] for desc in cur.description]
        title = dict(zip(columns, row))
        title["wfc_observations"] = _normalize_observations(title.get("wfc_observations"))
    finally:
        cur.close()
        conn.close()

    if request.method == "POST":
        new_gamespy_id = request.form.get("gamespy_id", "").strip()
        is_supported = int(request.form.get("is_supported", title.get("is_supported", 0)))
        is_featured = bool(request.form.get("is_featured"))

        if "remove_obs" in request.form:
            observations = []
        else:
            obs_title = request.form.get("obs_title", "").strip()
            obs_description = request.form.get("obs_description", "").strip()
            obs_icon = request.form.get("obs_icon", "info").strip() or "info"
            if obs_title and obs_description:
                observations = [{"title": obs_title, "description": obs_description, "icon": obs_icon}]
            else:
                observations = []

        conn = psycopg2.connect(config.db_url)
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE titles
                SET gamespy_id = %s,
                    is_supported = %s,
                    is_featured = %s,
                    wfc_observations = %s
                WHERE game_id = %s
                """,
                [new_gamespy_id, is_supported, is_featured, Json(observations), game_id],
            )
            conn.commit()
            flash("Game updated successfully.")
        except Exception as e:
            conn.rollback()
            flash(f"Error updating game: {e}")
        finally:
            cur.close()
            conn.close()
        return redirect(url_for("moderation.moderation_edit", game_id=game_id))

    user_info = get_logged_in_user_info()
    return render_template(
        "pages/moderation_edit.html",
        user_info=user_info,
        title=title,
    )
