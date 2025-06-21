# coding: utf-8
from flask import Flask, render_template, request, redirect, url_for, send_file, abort, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from email.header import Header
from email.utils import formataddr
import os
import csv
import io

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")

# Настройки за база данни
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///requests.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Настройки за имейл
app.config['MAIL_SERVER'] = 'trot.bg'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = 'noreply@trot.bg'
app.config['MAIL_PASSWORD'] = os.environ.get('NOREPLY_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'noreply@trot.bg'

mail = Mail(app)
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

class Admin(UserMixin):
    id = 1
    username = "admin"
    password = os.environ.get("ADMIN_PASSWORD")

@login_manager.user_loader
def load_user(user_id):
    if user_id == "1":
        return Admin()
    return None

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form['username'] == Admin.username and request.form['password'] == Admin.password:
            login_user(Admin())
            return redirect(url_for('admin_panel'))
        flash("Грешни данни за вход", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        message = request.form.get("message")

        new_request = ServiceRequest(name=name, email=email, message=message)
        db.session.add(new_request)
        db.session.commit()

        try:
            sender_name = str(Header("TROT.BG", 'utf-8'))
            sender_email = "noreply@trot.bg"
            formatted_sender = formataddr((sender_name, sender_email))

            admin_msg = Message(
                subject="=?utf-8?b?" + Header(f"Запитване от {name} - TROT", 'utf-8').encode() + "?=",
                recipients=["dimchev.ilia@gmail.com"],
                body=f"Name: {name}\nEmail: {email}\nMessage: {message}",
                sender=formatted_sender,
                charset='utf-8')

            mail.send(admin_msg)

            confirmation = Message(
                subject="=?utf-8?b?" + Header("TROT.BG - Потвърждение на запитване", 'utf-8').encode() + "?=",
                recipients=[email],
                sender=formatted_sender,
                charset='utf-8')

            confirmation.body = render_template("email_confirmation.txt", name=name)
            confirmation.html = render_template("email_confirmation.html", name=name)

            mail.send(confirmation)
        except Exception as e:
            print("Email sending error:", e)

        return redirect(url_for("thank_you"))
    return render_template("index.html")

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")

@app.route("/admin")
@login_required
def admin_panel():
    requests = ServiceRequest.query.order_by(ServiceRequest.id.desc()).all()
    return render_template("admin.html", requests=requests)

@app.route("/admin/delete/<int:request_id>", methods=["POST"])
@login_required
def delete_request(request_id):
    req = ServiceRequest.query.get_or_404(request_id)
    db.session.delete(req)
    db.session.commit()
    flash("Запитването е изтрито.")
    return redirect(url_for("admin_panel"))

@app.route("/admin/export")
@login_required
def export_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Име", "Имейл", "Съобщение"])

    for req in ServiceRequest.query.all():
        writer.writerow([req.id, req.name, req.email, req.message])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype='text/csv',
                     download_name='trot_requests.csv',
                     as_attachment=True)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
