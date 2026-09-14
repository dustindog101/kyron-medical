import os
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from app.config import Config
from app.database import init_db
from app.api.patients import patients_bp
from app.api.routing import routing_bp
from app.api.slots import slots_bp
from app.api.appointments import appointments_bp
from app.api.calls import calls_bp

def create_app(test_config=None):
    # Determine frontend directory
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    frontend_dir = os.path.join(base_dir, "frontend")

    app = Flask(__name__, static_folder=frontend_dir, static_url_path="")
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Enable CORS for frontend dashboard & external webhook callers
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize Database tables
    init_db()

    # Register API Blueprints
    app.register_blueprint(patients_bp)
    app.register_blueprint(routing_bp)
    app.register_blueprint(slots_bp)
    app.register_blueprint(appointments_bp)
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

    # Serve the call review frontend if requested via root
    @app.route("/")
    def index():
        if os.path.exists(os.path.join(frontend_dir, "index.html")):
            return send_from_directory(frontend_dir, "index.html")
        return jsonify({
            "message": "Kyron Medical Voice Scheduling Agent Backend API",
            "docs": "/api/protocols/summary",
            "health": "/health",
        }), 200

    return app
