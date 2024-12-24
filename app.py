from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import json
import os
import sys
import logging
import threading
from logging.handlers import RotatingFileHandler
from gevent import pywsgi
import io
import qrcode
from PIL import Image
import sqlite3

# Initialize logging
if not os.path.exists('logs'):
    os.makedirs('logs')

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]',
    handlers=[
        RotatingFileHandler('logs/app.log', maxBytes=10000, backupCount=10),
        logging.StreamHandler()
    ]
)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
logger = app.logger

# Version number
VERSION = "1.2.0"  # IP-based isolation with QR codes and analytics

# Initialize SQLite database
def init_db():
    db_path = os.path.join(os.path.dirname(__file__), 'analytics.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS analytics
                 (date TEXT, views INTEGER, unique_users INTEGER)''')
    conn.commit()
    conn.close()

# Update analytics
def update_analytics(ip):
    db_path = os.path.join(os.path.dirname(__file__), 'analytics.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Get or create today's record
    c.execute('SELECT * FROM analytics WHERE date = ?', (today,))
    record = c.fetchone()
    
    if record:
        c.execute('UPDATE analytics SET views = views + 1 WHERE date = ?', (today,))
    else:
        c.execute('INSERT INTO analytics (date, views, unique_users) VALUES (?, 1, 0)', (today,))
    
    conn.commit()
    conn.close()

# Get analytics data
def get_analytics():
    db_path = os.path.join(os.path.dirname(__file__), 'analytics.db')
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Get total views
    c.execute('SELECT SUM(views) FROM analytics')
    total_views = c.fetchone()[0] or 0
    
    # Get today's views
    today = datetime.now().strftime('%Y-%m-%d')
    c.execute('SELECT views FROM analytics WHERE date = ?', (today,))
    daily_views = c.fetchone()
    daily_views = daily_views[0] if daily_views else 0
    
    # Count unique users (using active clients)
    unique_users = len(set(clients_by_ip.keys()))
    
    conn.close()
    
    return {
        'views': total_views,
        'unique_users': unique_users,
        'daily_views': daily_views,
        'online_devices': sum(len(clients) for clients in clients_by_ip.values())
    }

# Initialize database on startup
init_db()

# In-memory storage
content_by_ip = {}
clients_by_ip = {}
analytics_lock = threading.Lock()

def get_client_ip():
    """Get client IP address"""
    return request.headers.get('X-Real-IP') or request.remote_addr

@app.route('/')
def index():
    """Render main page"""
    ip = get_client_ip()
    update_analytics(ip)
    return render_template('index.html', 
                         content=content_by_ip.get(ip, ''),
                         analytics=get_analytics(),
                         version=VERSION)

@app.route('/content', methods=['GET', 'POST'])
def handle_content():
    """Handle content updates"""
    ip = get_client_ip()
    
    if request.method == 'POST':
        content = request.json.get('content', '')
        content_by_ip[ip] = content
        return jsonify({'status': 'ok'})
    else:
        return jsonify({
            'content': content_by_ip.get(ip, ''),
            'analytics': get_analytics()
        })

@app.route('/qr')
def generate_qr():
    """Generate QR code for current URL"""
    try:
        ip = get_client_ip()
        url = f"{request.url_root}?ip={ip}"
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(url)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        return send_file(img_buffer, mimetype='image/png')
    except Exception as e:
        logger.error(f"QR code generation error: {str(e)}")
        return str(e), 500

@app.route('/debug')
def debug():
    """Show debug information"""
    try:
        analytics = get_analytics()
        system_info = {
            'python_version': sys.version,
            'platform': sys.platform,
            'active_connections': sum(len(clients) for clients in clients_by_ip.values())
        }
        
        # Get recent logs
        recent_logs = []
        if os.path.exists('logs/app.log'):
            with open('logs/app.log', 'r') as f:
                recent_logs = f.readlines()[-50:]  # Last 50 lines
        
        debug_info = {
            'analytics': analytics,
            'active_connections': {
                'total': sum(len(clients) for clients in clients_by_ip.values()),
                'by_ip': {ip: len(clients_list) for ip, clients_list in clients_by_ip.items()}
            },
            'system_info': {
                'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'content_store_size': len(content_by_ip)
            }
        }
        
        return render_template('debug.html',
                            system_info=system_info,
                            analytics=analytics,
                            recent_logs=recent_logs,
                            debug_info=debug_info)
    except Exception as e:
        logger.error(f"Debug page error: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 5050), app)
    print("Server starting on http://localhost:5050")
    server.serve_forever()
