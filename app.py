from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from ping3 import ping

app = Flask(__name__)
DATABASE_FILE = 'ping_monitor.db'
UI_DATABASE_FILE = 'ui_settings.db'

def create_table():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            hostname TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_ui_settings_table():
    conn = sqlite3.connect(UI_DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ui_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_id INTEGER NOT NULL,
            FOREIGN KEY (ip_id) REFERENCES ip_addresses(id)
        )
    ''')
    conn.commit()
    conn.close()

def insert_ip(ip: str, hostname: str):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ip_addresses (ip, hostname)
        VALUES (?, ?)
    ''', (ip, hostname))
    ip_id = cursor.lastrowid
    conn.commit()
    conn.close()
    insert_ui_setting(ip_id)

def insert_ui_setting(ip_id: int):
    conn = sqlite3.connect(UI_DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ui_settings (ip_id)
        VALUES (?)
    ''', (ip_id,))
    conn.commit()
    conn.close()

def load_ips():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, ip, hostname FROM ip_addresses')
    rows = cursor.fetchall()
    conn.close()
    return rows

def load_ordered_ips():
    conn = sqlite3.connect(DATABASE_FILE)
    ui_conn = sqlite3.connect(UI_DATABASE_FILE)
    cursor = conn.cursor()
    ui_cursor = ui_conn.cursor()
    ui_cursor.execute('SELECT ip_id FROM ui_settings ORDER BY id')
    ordered_ip_ids = ui_cursor.fetchall()
    ordered_ips = []
    for (ip_id,) in ordered_ip_ids:
        cursor.execute('SELECT id, ip, hostname FROM ip_addresses WHERE id = ?', (ip_id,))
        ip_info = cursor.fetchone()
        if ip_info:
            ordered_ips.append(ip_info)
    conn.close()
    ui_conn.close()
    return ordered_ips

def ping_ip(ip: str):
    try:
        response = ping(ip, timeout=1, unit='ms')
        if response is not None:
            return round(response, 2)
        return None
    except Exception:
        return None

@app.route('/')
def index():
    ips = load_ordered_ips()
    ping_results = {ip: ping_ip(ip) for _, ip, _ in ips}
    return render_template('index.html', ips=ips, ping_results=ping_results)

@app.route('/insert', methods=['GET', 'POST'])
def insert():
    if request.method == 'POST':
        ip = request.form['ip']
        hostname = request.form['hostname']
        insert_ip(ip, hostname)
        return redirect(url_for('index'))
    return render_template('insert.html')

@app.route('/save_order', methods=['POST'])
def save_order():
    order = request.json.get('order')
    if order:
        conn = sqlite3.connect(UI_DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ui_settings')
        for idx, ip_id in enumerate(order):
            cursor.execute('''
                INSERT INTO ui_settings (id, ip_id)
                VALUES (?, ?)
            ''', (idx, ip_id))
        conn.commit()
        conn.close()
    return jsonify(status='success')

@app.route('/ping_status', methods=['GET'])
def ping_status():
    ips = load_ordered_ips()
    ping_results = {ip: ping_ip(ip) for _, ip, _ in ips}
    return jsonify(ping_results)

@app.route('/delete/<int:ip_id>', methods=['POST'])
def delete_ip(ip_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM ip_addresses WHERE id = ?', (ip_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/edit/<int:ip_id>', methods=['GET', 'POST'])
def edit_ip(ip_id):
    if request.method == 'POST':
        new_ip = request.form['ip']
        new_hostname = request.form['hostname']
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE ip_addresses SET ip = ?, hostname = ? WHERE id = ?', (new_ip, new_hostname, ip_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT ip, hostname FROM ip_addresses WHERE id = ?', (ip_id,))
        ip_info = cursor.fetchone()
        conn.close()
        return render_template('edit.html', ip_id=ip_id, ip=ip_info[0], hostname=ip_info[1])

if __name__ == "__main__":
    create_table()
    create_ui_settings_table()
    app.run(debug=True)
