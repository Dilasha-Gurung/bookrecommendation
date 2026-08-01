"""
Flask entry point.

Run (dev):
    cd backend
    pip install -r requirements.txt
    python app.py
"""
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from datetime import timedelta

from config import Config
from routes.auth import bp as auth_bp
from routes.books import bp as books_bp
from routes.recommendations import bp as recommendations_bp
from routes.pdf import bp as pdf_bp


def create_app():
    app = Flask(__name__)
    app.config["JWT_SECRET_KEY"] = Config.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=Config.JWT_ACCESS_TOKEN_EXPIRES_HOURS)

    JWTManager(app)
    CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

    app.register_blueprint(auth_bp)
    app.register_blueprint(books_bp)
    app.register_blueprint(recommendations_bp)
    app.register_blueprint(pdf_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000)
