"""
Lanceur pour le site StudioSowa.
Usage:  python run.py
Le site sera accessible à http://localhost:5000
"""
from app import app, db, seed_demo_projects
import os

if __name__ == '__main__':
    # Create upload folder if it doesn't exist
    os.makedirs(os.path.join(os.path.dirname(__file__), 'static', 'uploads'), exist_ok=True)

    with app.app_context():
        db.create_all()
        seed_demo_projects()

    print("=" * 50)
    print("  STUDIOSOWA — Serveur démarré")
    print("  Site public  : http://localhost:5000")
    print("  Administration: http://localhost:5000/admin")
    print("  Mot de passe admin : sowa2024!")
    print("  (Modifiable dans .env : ADMIN_PASSWORD=...)")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5000)
