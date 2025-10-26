from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from email.header import Header
from email.utils import formataddr
from werkzeug.utils import secure_filename
# import datetime
import time
import os
import csv
import io


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "secret")

# Настройки за база данни
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///requests.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Настройки за имейл
app.config['MAIL_SERVER'] = 'trot.bg'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.environ.get("SENDER_EMAIL")
app.config['MAIL_PASSWORD'] = os.environ.get('SENDER_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get("SENDER_EMAIL")

MAX_TOTAL_ATTACHMENT_SIZE = 25 * 1024 * 1024  # 25MB


mail = Mail(app)

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Модел за запитване
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.String(30), nullable=False)

# Потребител за админ
class Admin(UserMixin):
    id = 1
    username = os.environ.get("ADMIN_LOGIN")
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
        if request.form.get("website"):  # honeypot
            print("SPAM: Honeypot triggered")
            return redirect(url_for("thank_you"))
        
        if request.content_length > MAX_TOTAL_ATTACHMENT_SIZE:
            flash("Прикачените файлове не трябва да надхвърлят 25MB.", "error")
            return render_template("index.html",
                                   timestamp=time.time(),
                                   name=request.form.get("name"),
                                   email=request.form.get("email"),
                                   phone=request.form.get("phone"),
                                   message=request.form.get("message"),
                                   attachments=request.files.getlist("attachments"))        

        try:
            start_time = float(request.form.get("form_start", 0))
            if time.time() - start_time < 2:
                print("SPAM: Too fast")
                return redirect(url_for("thank_you"))
        except ValueError:
            return redirect(url_for("thank_you"))

        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        message = request.form.get("message")
        attachments = request.files.getlist("attachments")
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(time.time()))

        new_request = ServiceRequest(name=name, email=email, phone=phone, message=message, timestamp=timestamp)
        db.session.add(new_request)
        db.session.commit()

        try:
            # Красив "From" адрес
            sender_name = str(Header("TROT.BG", 'utf-8'))
            sender_email = os.environ.get("SENDER_EMAIL")
            formatted_sender = formataddr((sender_name, sender_email))

            admin_msg = Message(
            subject=str(Header(f"Запитване от {name}", 'utf-8')),
            recipients=["dimchev.ilia@gmail.com"],
            body=f"Име: {name}\nИмейл: {email}\nТелефон: {phone}\nПолучено на: {timestamp}\nСъобщение: {message}",
            sender=formatted_sender,
            charset='utf-8')

            for file in attachments:
                if file.filename:
                    filename = secure_filename(file.filename)
                    content = file.read()
                    admin_msg.attach(filename, file.content_type, content)

            mail.send(admin_msg)

            confirmation = Message(
            subject=str(Header("Получихме вашето запитване!", 'utf-8')),
            recipients=[email],
            sender=formatted_sender,
            charset='utf-8')
            
            confirmation.body = (
            f"Здравейте, {name}!\n\n"
            "Благодарим, че се свързахте с нас. Ще се свържем с вас възможно най-скоро!\n\n"
            "Поздрави,\nTROT.BG")

            confirmation.html = render_template("email_confirmation.html", name=name)

            mail.send(confirmation)

            connection = Message(
            subject=str(Header("Последвайте ни и в социалните мрежи!", 'utf-8')),
            recipients=[email],
            sender=formatted_sender,
            charset='utf-8')
            
            connection.body = (
            f"Здравейте, {name}!\n\n"
            "Ще се радваме да се свържем с Вас и в социалните мрежи, където също може да ни пишете.\n\n"
            "Facebook - https://www.facebook.com/profile.php?id=61575267604907\n"
            "Instagram - https://www.instagram.com/trotbg/\n\n"
            "Поздрави,\nTROT.BG")

            connection.html = render_template("email_connection.html", name=name)

            mail.send(connection)

            content = Message(
                subject=str(
                    Header("БОНУС! Как да открием точния размер гуми на електрическа тротинетка!", 'utf-8')),
                recipients=[email],
                sender=formatted_sender,
                charset='utf-8')

            content.body = (
                f"Здравейте, {name}!\n\n"
                "Сигурно сте се чудили какво означава размер от рода на 80/65-6\n\n"
                "Сега ще разбулим мистерията зад това съкращение при гумите на електрическите тротинетки!\n\n"
                "Размер на гуми 80/65-6 означава:\n"
                "- 80 е широчината на гумата в милиметри\n"
                "- 65 е 65% от широчината й (80), което е 52 милиметра и това е височината на страничната й стена\n"
                "- 6 е вътрешният й диаметър в инчове - 6 * 2.54 ни дава 15.24 в сантиметри\n\n"
                "Остава ни само да измерим вашата, за да узнаем размера й с точност.\n\n"
                "Поздрави,\nTROT.BG")

            content.html = render_template(
                "email_content.html", name=name)

            mail.send(content)

            #TODO: Add Connection and Content Messages
        except Exception as e:
            print("Exception:", e)
        
        return redirect(url_for("thank_you"))
    return render_template("index.html", timestamp=time.time())

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
    writer.writerow(["ID", "Име", "Имейл", "Съобщение", "Дата"])

    for req in ServiceRequest.query.all():
        writer.writerow([req.id, req.name, req.email, req.phone, req.message, req.timestamp])

    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype='text/csv',
                     download_name='trot_requests.csv',
                     as_attachment=True)

# Само за локална разработка
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)

