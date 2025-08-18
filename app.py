import os
import jwt
import datetime
import requests
from flask import Flask, redirect, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message

load_dotenv()

app = Flask(__name__)
app.secret_key = "jamanta"
app.config['SECRET_KEY'] = "jamanta"

# --- Configuração do Banco de Dados ---
DB_USER = "testuser"
DB_PASSWORD = "testpass"
DB_HOST = "localhost"
DB_NAME = "testdb"
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# --- Configuração do Flask-Mail ---
app.config['MAIL_SERVER'] = "smtp.googlemail.com"
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = "renangs2222@gmail.com"
app.config['MAIL_PASSWORD'] = "hfme nmyy imbs yuet"
mail = Mail(app)
# ----------------------------------------

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
CORS(app, origins=[FRONTEND_URL], supports_credentials=True)

GOOGLE_CLIENT_ID = "59996041222-kmvv2qckjdkkfp3c0maidcj3d5kapqoi.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"
REDIRECT_URI = "http://localhost:5000/login/google/authorized"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=True)
    picture = db.Column(db.String(255), nullable=True)

    def __repr__(self):
        return f'<User {self.email}>'


@app.route("/api/register", methods=["POST"])
def register_user():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not all([name, email, password]):
        return jsonify({"error": "Todos os campos são obrigatórios"}), 400

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Este e-mail já está cadastrado"}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    new_user = User(name=name, email=email, password_hash=hashed_password)

    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Usuário criado com sucesso!"}), 201


@app.route("/api/login", methods=["POST"])
def login_user():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "E-mail e senha são obrigatórios"}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"error": "Credenciais inválidas"}), 401

    if not user.password_hash:
        return jsonify({
            "error": "ACCOUNT_NO_PASSWORD",
            "message": "Esta conta foi criada usando o login do Google. Use o 'Esqueci minha senha' para criar uma senha."
        }), 403

    if bcrypt.check_password_hash(user.password_hash, password):
        jwt_token = jwt.encode({
            "user_id": user.id,
            "email": user.email,
            "name": user.name,
            "picture": user.picture,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, app.config["SECRET_KEY"], algorithm="HS256")

        return jsonify({"token": jwt_token})

    return jsonify({"error": "Credenciais inválidas"}), 401


@app.route('/api/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    user = User.query.filter_by(email=email).first()

    if user:
        reset_token = jwt.encode({
            "user_id": user.id,
            "purpose": "password-reset",
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=15)
        }, app.config["SECRET_KEY"], algorithm="HS256")

        reset_url = f"{FRONTEND_URL}/reset-password/{reset_token}"

        msg = Message("Redefinição de Senha - MeuApp",
                      sender=os.getenv('MAIL_USERNAME'),
                      recipients=[email])
        msg.body = f"Para redefinir (ou criar) sua senha, visite o seguinte link: {reset_url}\n\nSe você não solicitou isso, ignore este e-mail."

        try:
            mail.send(msg)
        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return jsonify({"error": "Não foi possível enviar o e-mail de redefinição."}), 500

    return jsonify({"message": "Se um usuário com este e-mail existir, um link de redefinição foi enviado."}), 200


@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('password')

    if not token or not new_password:
        return jsonify({"error": "Token e nova senha são necessários."}), 400

    try:
        payload = jwt.decode(token, app.config["SECRET_KEY"], algorithms=["HS256"])

        if payload.get("purpose") != "password-reset":
            return jsonify({"error": "Token inválido para esta operação."}), 401

        user_id = payload['user_id']
        user = User.query.get(user_id)

        if not user:
            return jsonify({"error": "Usuário não encontrado."}), 404

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.password_hash = hashed_password
        db.session.commit()

        return jsonify({"message": "Senha atualizada com sucesso!"}), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"error": "O link de redefinição expirou."}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "O link de redefinição é inválido."}), 401


@app.route("/login/google")
def login_google():
    google_auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?response_type=code&client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        "&scope=openid%20email%20profile%20https://www.googleapis.com/auth/calendar"
        "&access_type=offline&prompt=consent"
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

    user_email = user_info.get("email")
    user = User.query.filter_by(email=user_email).first()

    if not user:
        user = User(
            email=user_email,
            name=user_info.get("name"),
            picture=user_info.get("picture")
        )
        db.session.add(user)
        db.session.commit()

    jwt_token = jwt.encode({
        "user_id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
        "locale": user_info.get("locale", "pt-BR"),
        "verified_email": user_info.get("email_verified"),
        "google_access_token": access_token,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, app.config["SECRET_KEY"], algorithm="HS256")

    return redirect(f"{FRONTEND_URL}/auth/callback?token={jwt_token}")


@app.route("/api/profile")
def profile():
    token_data = get_jwt()
    if isinstance(token_data, tuple):
        return token_data
    return jsonify({"user": token_data})


@app.route("/api/calendar")
def list_events():
    token_data = get_jwt()
    if isinstance(token_data, tuple):
        return token_data

    google_token = token_data.get("google_access_token")
    if not google_token:
        return jsonify({"error": "Acesso ao calendário requer login com Google"}), 403

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
    google_token = token.get("google_access_token")
    if not google_token:
        return jsonify({"error": "Acesso ao calendário requer login com Google"}), 403
    event_data = request.json
    resp = requests.post(
        "https://www.googleapis.com/calendar/v3/calendars/primary/events",
        headers={"Authorization": f"Bearer {google_token}", "Content-Type": "application/json"},
        params={"conferenceDataVersion": 1},
        json=event_data
    )
    return jsonify(resp.json())


@app.route("/api/calendar/<event_id>", methods=["PUT"])
def update_event(event_id):
    token = get_jwt()
    if isinstance(token, tuple):
        return token
    google_token = token.get("google_access_token")
    if not google_token:
        return jsonify({"error": "Acesso ao calendário requer login com Google"}), 403
    event_data = request.json
    resp = requests.put(
        f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
        headers={"Authorization": f"Bearer {google_token}", "Content-Type": "application/json"},
        json=event_data
    )
    return jsonify(resp.json())


@app.route("/api/calendar/<event_id>", methods=["DELETE"])
def delete_event(event_id):
    token = get_jwt()
    if isinstance(token, tuple):
        return token
    google_token = token.get("google_access_token")
    if not google_token:
        return jsonify({"error": "Acesso ao calendário requer login com Google"}), 403
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
    with app.app_context():
        db.create_all()
    app.run(debug=True)