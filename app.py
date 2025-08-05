import os
import jwt
import datetime
import requests
from flask import Flask, redirect, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "jamanta"
app.config['SECRET_KEY'] = "jamanta"

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
CORS(app, origins=[FRONTEND_URL])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "59996041222-kmvv2qckjdkkfp3c0maidcj3d5kapqoi.apps.googleusercontent.com")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "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")
REDIRECT_URI = "http://localhost:5000/login/google/authorized"

@app.route("/login/google")
def login_google():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        "?response_type=code"
        f"&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&scope=openid%20email%20profile%20https://www.googleapis.com/auth/calendar"
        "&access_type=offline"
        "&prompt=consent"
    )
    return redirect(google_auth_url)

@app.route("/login/google/authorized")
def google_authorized():
    code = request.args.get("code")
    if not code:
        return jsonify({"error": "Código de autorização não encontrado"}), 400

    token_resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    ).json()

    access_token = token_resp.get("access_token")
    if not access_token:
        return jsonify({"error": "Falha ao obter token do Google"}), 400

    user_info = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    jwt_token = jwt.encode({
        "user_id": user_info.get("sub"),
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "locale": user_info.get("locale", "pt-BR"),
        "verified_email": user_info.get("email_verified"),
        "google_access_token": access_token,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return redirect(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")

@app.route("/api/profile")
def profile():
    token = get_jwt()
    if isinstance(token, tuple):
        return token
    return jsonify({"user": token})

@app.route("/api/calendar")
def list_events():
    token = get_jwt()
    if isinstance(token, tuple):
        return token

    google_token = token.get("google_access_token")
    events_resp = requests.get(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={"Authorization": f"Bearer {google_token}"}
    ).json()

    return jsonify(events_resp)

@app.route("/api/calendar", methods=["POST"])
def create_event():
    token = get_jwt()
    if isinstance(token, tuple):
        return token

    event_data = request.json
    google_token = token.get("google_access_token")
    resp = requests.post(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={
            "Authorization": f"Bearer {google_token}",
            "Content-Type": "application/json"
        },
        params={"conferenceDataVersion": 1},  # Aqui está a correção importante!
        json=event_data
    )
    return jsonify(resp.json())

@app.route("/api/calendar/<event_id>", methods=["PUT"])
def update_event(event_id):
    token = get_jwt()
    if isinstance(token, tuple):
        return token

    event_data = request.json
    google_token = token.get("google_access_token")
    resp = requests.put(
        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
        headers={
            "Authorization": f"Bearer {google_token}",
            "Content-Type": "application/json"
        },
        json=event_data
    )
    return jsonify(resp.json())

@app.route("/api/calendar/<event_id>", methods=["DELETE"])
def delete_event(event_id):
    token = get_jwt()
    if isinstance(token, tuple):
        return token

    google_token = token.get("google_access_token")
    resp = requests.delete(
        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
        headers={"Authorization": f"Bearer {google_token}"}
    )

    return jsonify({"deleted": resp.status_code == 204})

def get_jwt():
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return jsonify({"message": "Token ausente"}), 401
    try:
        token = auth_header.split(" ")[1]
        return jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token expirado"}), 401
    except Exception:
        return jsonify({"message": "Token inválido"}), 401

if __name__ == "__main__":
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    app.run(debug=True)