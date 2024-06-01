import os
import requests
import sqlite3
from flask import Flask, render_template, redirect, url_for, flash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from email_validator import validate_email, EmailNotValidError
from wtforms import ValidationError

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Fonction pour récupérer les données de l'API
def get_cat_data():
    url = "https://api.thecatapi.com/v1/breeds"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# Fonction pour former l'URL de l'image
def get_image_url(image_id):
    base_url = "https://cdn2.thecatapi.com/images/"
    return base_url + image_id + ".jpg"

# Route pour mettre à jour la base de données avec les données de l'API
@app.route('/update_database')
def update_database():
    data = get_cat_data()
    if data:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("DROP TABLE IF EXISTS cats")
        c.execute('''CREATE TABLE cats (
                     id INTEGER PRIMARY KEY,
                     name TEXT,
                     description TEXT,
                     image_url TEXT
                     )''')
        for cat in data:
            image_id = cat.get('reference_image_id', '')  # Récupérer l'identifiant de l'image
            image_url = get_image_url(image_id) if image_id else ''  # Former l'URL de l'image
            c.execute("INSERT INTO cats (name, description, image_url) VALUES (?, ?, ?)",
                      (cat['name'], cat.get('description', ''), image_url))
        conn.commit()
        conn.close()
        return "Database updated successfully"
    else:
        return "Failed to update database"

# Fonction pour récupérer les données des races de chats depuis la base de données
def get_cats_from_database():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM cats")
    cats = c.fetchall()
    conn.close()
    return cats

# Route pour afficher les données des races de chats
@app.route('/cats')
def cats():
    cats = get_cats_from_database()
    return render_template('cats.html', cats=cats)

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS cats (
            id INTEGER PRIMARY KEY,
            name TEXT,
            description TEXT,
            image_url TEXT
        )
    ''')
    conn.commit()
    conn.close()

# User model
class User(UserMixin):
    def __init__(self, id, email, password):
        self.id = id
        self.email = email
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    if user:
        return User(id=user[0], email=user[1], password=user[2])
    return None

# Validation des adresses e-mail
class UniqueEmail:
    def __init__(self, message=None):
        if not message:
            message = 'Email address already registered'
        self.message = message

    def __call__(self, form, field):
        email = field.data
        try:
            validate_email(email)
        except EmailNotValidError:
            raise ValidationError('Invalid email address')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()
        if user:
            raise ValidationError(self.message)

# Formulaires
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), UniqueEmail()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

# Routes d'inscription
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data
        password = generate_password_hash(form.password.data, method='pbkdf2:sha256')

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            flash('Email address already registered')
            return redirect(url_for('register'))
        conn.close()

        flash('Registration successful! Please log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

# Routes de connexion
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if user and check_password_hash(user[2], password):
            login_user(User(id=user[0], email=user[1], password=user[2]))
            return redirect(url_for('cats'))
        flash('Invalid email or password')
    return render_template('login.html', form=form)

# Route de déconnexion
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Route de l'accueil redirigeant
@app.route('/')
def home():
    return redirect(url_for('cats'))

# Initialiser la base de données et lancer l'application
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
