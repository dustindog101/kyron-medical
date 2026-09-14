import os
from app import create_app
from app.seed import seed_database
from app.database import SessionLocal
from app.models import Doctor

app = create_app()

# Automatically seed if database is empty
with app.app_context():
    db = SessionLocal()
    try:
        if db.query(Doctor).count() == 0:
            print("No physicians found. Running seed_database()...")
            seed_database()
    finally:
        db.close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="0.0.0.0", port=port, debug=debug, use_reloader=False)
