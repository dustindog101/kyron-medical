import os
from flask import Flask, jsonify, send_from_directory, redirect
from flask_cors import CORS
from app.config import Config
from app.database import init_db
from app.api.patients import patients_bp
from app.api.routing import routing_bp
from app.api.slots import slots_bp
from app.api.appointments import appointments_bp
from app.api.providers import providers_bp
from app.api.calls import calls_bp

def create_app(test_config=None):
    # Frontend directory resolution
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    legacy_dir = os.environ.get("FRONTEND_DIR", os.path.join(base_dir, "frontend"))
    draft_dir = os.environ.get("FRONTEND_DRAFT_DIR", os.path.join(base_dir, "frontend-draft", "dist"))
    primary_frontend = os.environ.get("PRIMARY_FRONTEND", "legacy").strip().lower()

    active_root_dir = draft_dir if primary_frontend == "draft" else legacy_dir

    app = Flask(__name__, static_folder=active_root_dir, static_url_path="")
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Enable CORS for frontend dashboard & external webhook callers
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database tables
    init_db()

    # Automatically seed clinical protocols and doctors if starting with a fresh database
    if not test_config:
        from app.database import SessionLocal
        from app.models import Doctor
        db = SessionLocal()
        try:
            if db.query(Doctor).count() == 0:
                from app.seed import seed_database
                seed_database()
        except Exception:
            pass
        finally:
            db.close()

    # Register API Blueprints
    app.register_blueprint(patients_bp)
    app.register_blueprint(routing_bp)
    app.register_blueprint(slots_bp)
    app.register_blueprint(appointments_bp)
    app.register_blueprint(providers_bp)
    app.register_blueprint(calls_bp)

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({
            "status": "healthy",
            "service": "Kyron Medical Scheduling API",
            "version": "1.0.0",
        }), 200

    @app.route("/api/protocols/summary", methods=["GET"])
    def protocols_summary():
        from app.database import SessionLocal
        from app.models import Doctor, Location
        db = SessionLocal()
        try:
            doctors = db.query(Doctor).all()
            locations = db.query(Location).all()
            return jsonify({
                "locations": [loc.to_dict() for loc in locations],
                "doctors": [doc.to_dict() for doc in doctors],
            }), 200
        finally:
            db.close()

    # Dual Frontend Architecture (Legacy + Draft)
    @app.route("/draft")
    def draft_redirect():
        return redirect("/draft/", code=302)

    @app.route("/draft/")
    @app.route("/draft/<path:path>")
    def serve_draft(path=""):
        if path and os.path.exists(os.path.join(draft_dir, path)):
            return send_from_directory(draft_dir, path)
        if os.path.exists(os.path.join(draft_dir, "index.html")):
            return send_from_directory(draft_dir, "index.html")
        return jsonify({"error": "Draft frontend not found or not compiled"}), 404

    @app.route("/legacy")
    def legacy_redirect():
        return redirect("/legacy/", code=302)

    @app.route("/legacy/")
    @app.route("/legacy/<path:path>")
    def serve_legacy(path=""):
        if path and os.path.exists(os.path.join(legacy_dir, path)):
            return send_from_directory(legacy_dir, path)
        if os.path.exists(os.path.join(legacy_dir, "index.html")):
            return send_from_directory(legacy_dir, "index.html")
        return jsonify({"error": "Legacy frontend not found"}), 404

    @app.route("/assets/<path:path>")
    def serve_root_assets(path):
        if os.path.exists(os.path.join(active_root_dir, "assets", path)):
            return send_from_directory(os.path.join(active_root_dir, "assets"), path)
        if os.path.exists(os.path.join(draft_dir, "assets", path)):
            return send_from_directory(os.path.join(draft_dir, "assets"), path)
        return jsonify({"error": "Asset not found"}), 404

    # Serve the primary call review frontend if requested via root /
    @app.route("/")
    def index():
        if os.path.exists(os.path.join(active_root_dir, "index.html")):
            return send_from_directory(active_root_dir, "index.html")
        return jsonify({
            "message": "Kyron Medical Voice Scheduling Agent Backend API",
            "docs": "/api/protocols/summary",
            "health": "/health",
        }), 200

    return app
