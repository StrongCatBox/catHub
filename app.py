import requests
import sqlite3
from flask import Flask, render_template

app = Flask(__name__)

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

if __name__ == '__main__':
    app.run(debug=True)
