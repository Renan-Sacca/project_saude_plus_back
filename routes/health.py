from datetime import datetime, timezone
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)

@health_bp.get("/health")
def health():
    return jsonify({"ok": True, "time": datetime.now(timezone.utc).isoformat()})
