from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
from ping3 import ping
import time
import threading
from datetime import datetime

app = Flask(__name__)
DATABASE_FILE = 'network-status.db'

def create_tables():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_addresses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT NOT NULL,
            hostname TEXT,
            category TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ping_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_id INTEGER,
            response_time REAL,
            timestamp INTEGER,
            FOREIGN KEY (ip_id) REFERENCES ip_addresses(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ui_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_id INTEGER NOT NULL,
            FOREIGN KEY (ip_id) REFERENCES ip_addresses(id)
        )
    ''')
    conn.commit()
    conn.close()

def insert_ip(ip: str, hostname: str, category: str):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ip_addresses (ip, hostname, category)
        VALUES (?, ?, ?)
    ''', (ip, hostname, category))
    ip_id = cursor.lastrowid
    conn.commit()
    conn.close()
    insert_ui_setting(ip_id)

def edit_ip(ip_id: int, new_ip: str, new_hostname: str, new_category: str):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE ip_addresses
        SET ip = ?, hostname = ?, category = ?
        WHERE id = ?
    ''', (new_ip, new_hostname, new_category, ip_id))
    conn.commit()
    conn.close()

def insert_ui_setting(ip_id: int):
    conn = sqlite3.connect(DATABASE_FILE)
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
    cursor.execute('SELECT id, ip, hostname, category FROM ip_addresses')
    rows = cursor.fetchall()
    conn.close()
    return rows

def load_ordered_ips():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT ip_id FROM ui_settings ORDER BY rowid')
    ordered_ip_ids = cursor.fetchall()

    ordered_ips = []
    for (ip_id,) in ordered_ip_ids:
        cursor.execute('SELECT id, ip, hostname, category FROM ip_addresses WHERE id = ?', (ip_id,))
        ip_info = cursor.fetchone()
        if ip_info:
            ordered_ips.append(ip_info)

    conn.close()
    
    return ordered_ips

def ping_ip(ip: str):
    try:
        response = ping(ip, timeout=1, unit='ms')
        if response is not None:
            return round(response, 3)
        return None
    except Exception:
        return None

def record_ping_response(ip_id: int, response_time: float):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ping_responses (ip_id, response_time, timestamp)
        VALUES (?, ?, ?)
    ''', (ip_id, response_time, int(time.time())))
    conn.commit()
    conn.close()

def get_ip_id_by_ip(ip: str):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM ip_addresses WHERE ip = ?', (ip,))
    ip_id = cursor.fetchone()[0]
    conn.close()
    return ip_id

def ping_all_ips():
    while True:
        ips = load_ips()
        for ip_info in ips:
            ip_id, ip, _, _ = ip_info
            response_time = ping_ip(ip)
            if response_time is not None:
                record_ping_response(ip_id, response_time)
        time.sleep(15)

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    return datetime.fromtimestamp(value).strftime(format)

@app.route('/')
def index():
    ips = load_ordered_ips()
    categories = set(ip[3] for ip in ips)
    
    latest_ping_results = {}
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    for ip in ips:
        cursor.execute('''
            SELECT response_time, timestamp
            FROM ping_responses
            WHERE ip_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (ip[0],))
        result = cursor.fetchone()
        if result:
            latest_ping_results[ip[0]] = {
                'response_time': result[0],
                'timestamp': datetime.fromtimestamp(result[1]).strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            latest_ping_results[ip[0]] = {
                'response_time': 'No data',
                'timestamp': 'No data'
            }
    
    conn.close()
    return render_template('index.html', ips=ips, categories=categories, latest_ping_results=latest_ping_results)

@app.route('/add', methods=['GET', 'POST'])
def insert():
    if request.method == 'POST':
        ip = request.form['ip']
        hostname = request.form['hostname']
        category = request.form['category']
        insert_ip(ip, hostname, category)
        return redirect(url_for('index'))
    return render_template('add.html')

@app.route('/save', methods=['POST'])
def save_order():
    order = request.json.get('order')
    if order:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ui_settings')
        for idx, ip_id in enumerate(order):
            cursor.execute('''
                INSERT INTO ui_settings (ip_id)
                VALUES (?)
            ''', (ip_id,))
        conn.commit()
        conn.close()
    return jsonify(status='success')

@app.route('/results', methods=['GET'])
def latest_ping_results():
    ips = load_ordered_ips()
    latest_ping_results = {}
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    
    for ip in ips:
        cursor.execute('''
            SELECT response_time, timestamp
            FROM ping_responses
            WHERE ip_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (ip[0],))
        result = cursor.fetchone()
        if result:
            latest_ping_results[ip[0]] = {
                'response_time': result[0],
                'timestamp': datetime.fromtimestamp(result[1]).strftime('%Y-%m-%d %H:%M:%S')
            }
        else:
            latest_ping_results[ip[0]] = {
                'response_time': 'No data',
                'timestamp': 'No data'
            }
    
    conn.close()
    return jsonify(latest_ping_results)

@app.route('/delete/<int:ip_id>', methods=['POST'])
def delete_ip(ip_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    try:
        cursor.execute('BEGIN TRANSACTION')
        cursor.execute('DELETE FROM ip_addresses WHERE id = ?', (ip_id,))
        cursor.execute('DELETE FROM ping_responses WHERE ip_id = ?', (ip_id,))
        cursor.execute('DELETE FROM ui_settings WHERE ip_id = ?', (ip_id,))
        conn.commit()
        return redirect(url_for('index'))
    except Exception as e:
        conn.rollback()
        print("Error:", e)
    finally:
        conn.close()


@app.route('/edit/<int:ip_id>', methods=['GET', 'POST'])
def edit_ip(ip_id):
    if request.method == 'POST':
        new_ip = request.form['ip']
        new_hostname = request.form['hostname']
        new_category = request.form['category']
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('UPDATE ip_addresses SET ip = ?, hostname = ?, category = ? WHERE id = ?', (new_ip, new_hostname, new_category, ip_id))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))
    else:
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT ip, hostname, category FROM ip_addresses WHERE id = ?', (ip_id,))
        ip_info = cursor.fetchone()
        conn.close()
        return render_template('edit.html', ip_id=ip_id, ip=ip_info[0], hostname=ip_info[1], category=ip_info[2])

@app.route('/view/<int:ip_id>')
def view_ping_responses(ip_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT ip, hostname, category FROM ip_addresses WHERE id = ?', (ip_id,))
    ip_info = cursor.fetchone()
    cursor.execute('SELECT response_time, timestamp FROM ping_responses WHERE ip_id = ? ORDER BY timestamp DESC', (ip_id,))
    ping_responses = cursor.fetchall()
    conn.close()

    response_times = [response[0] for response in ping_responses]
    timestamps = [datetime.fromtimestamp(response[1]).strftime('%Y-%m-%dT%H:%M:%S') for response in ping_responses]

    return render_template('view.html', ip_info=ip_info, ping_responses=ping_responses, response_times=response_times, timestamps=timestamps)

if __name__ == "__main__":
    create_tables()
    ping_thread = threading.Thread(target=ping_all_ips)
    ping_thread.daemon = True
    ping_thread.start()
    app.run(host="0.0.0.0", port=8000, debug=True)
