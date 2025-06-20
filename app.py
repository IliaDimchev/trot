from flask import Flask, render_template, request, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from dotenv import load_dotenv

import os
load_dotenv()

app = Flask(__name__)

# Настройки за база данни
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///requests.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Модел за запитване
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

# Настройки за имейл
app.config['MAIL_SERVER'] = 'smtp.abv.bg'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True  # Вместо TLS
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')

mail = Mail(app)

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        # Запазване в база данни
        new_request = ServiceRequest(name=name, email=email, message=message)
        db.session.add(new_request)
        db.session.commit()

        # Изпращане на имейл
        msg = Message("Ново запитване от TROT", recipients=["your@email.com"])
        msg.body = f"Име: {name}\nИмейл: {email}\nСъобщение: {message}"
        mail.send(msg)

        # Потвърдителен имейл към клиента
        confirmation = Message("Благодарим за запитването към TROT",
                       recipients=[email])
        
        confirmation.body = (
            f"Здравейте, {name}!\n\n"
            "Благодарим, че се свързахте с нас! Ще се свържем с Вас възможно най-скоро.\n\n"
         "Поздрави,\nTROT.BG"
        )

        mail.send(confirmation)

        return redirect(url_for("thank_you"))
    return render_template("index.html")

@app.route("/admin")
def admin_panel():
    password = request.args.get("pass")
    if password != os.environ.get("ADMIN_PASSWORD"):
        abort(403)

    requests = ServiceRequest.query.order_by(ServiceRequest.id.desc()).all()
    return render_template("admin.html", requests=requests)

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
