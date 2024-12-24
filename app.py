from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime, timedelta
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
    """Initialize database"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'analytics.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Create tables if not exist
        c.execute('''CREATE TABLE IF NOT EXISTS analytics
                     (key TEXT PRIMARY KEY, value INTEGER)''')
        c.execute('''CREATE TABLE IF NOT EXISTS visits
                     (ip TEXT, timestamp TEXT)''')
        
        # Initialize total_views if not exists
        c.execute('INSERT OR IGNORE INTO analytics (key, value) VALUES ("total_views", 0)')
        c.execute('INSERT OR IGNORE INTO analytics (key, value) VALUES ("total_syncs", 0)')
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")

# Update analytics
def update_analytics(ip):
    """Update analytics data"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'analytics.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Update total views - using INSERT OR REPLACE with COALESCE
        c.execute('''
            INSERT OR REPLACE INTO analytics (key, value)
            VALUES ("total_views", 
                COALESCE(
                    (SELECT value + 1 FROM analytics WHERE key = "total_views"),
                    1
                )
            )
        ''')
        
        # Update daily views
        today = datetime.now().strftime('%Y-%m-%d')
        daily_key = f"daily_views_{today}"
        c.execute('''
            INSERT OR REPLACE INTO analytics (key, value)
            VALUES (?, 
                COALESCE(
                    (SELECT value + 1 FROM analytics WHERE key = ?),
                    1
                )
            )
        ''', (daily_key, daily_key))
        
        # Record visit with timestamp
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        c.execute('INSERT INTO visits (ip, timestamp) VALUES (?, ?)', (ip, now))
        
        # Update total syncs when content is updated
        if request and request.endpoint == 'handle_content' and request.method == 'POST':
            c.execute('''
                INSERT OR REPLACE INTO analytics (key, value)
                VALUES ("total_syncs", 
                    COALESCE(
                        (SELECT value + 1 FROM analytics WHERE key = "total_syncs"),
                        1
                    )
                )
            ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating analytics: {str(e)}")

# Get analytics data
def get_analytics():
    """Get analytics data"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), 'analytics.db')
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        # Get total views
        c.execute('SELECT value FROM analytics WHERE key = "total_views"')
        result = c.fetchone()
        total_views = result[0] if result else 0
        
        # Get today's views
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('SELECT value FROM analytics WHERE key = ?', (f"daily_views_{today}",))
        result = c.fetchone()
        daily_views = result[0] if result else 0
        
        # Get unique devices in last hour
        hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
        c.execute('SELECT COUNT(DISTINCT ip) FROM visits WHERE timestamp > ?', (hour_ago,))
        result = c.fetchone()
        online_devices = result[0] if result else 0
        
        # Get total unique visitors
        c.execute('SELECT COUNT(DISTINCT ip) FROM visits')
        result = c.fetchone()
        total_unique_visitors = result[0] if result else 0
        
        # Get total content syncs (number of content updates)
        c.execute('SELECT value FROM analytics WHERE key = "total_syncs"')
        result = c.fetchone()
        total_syncs = result[0] if result else 0
        
        conn.close()
        
        return {
            'views': total_views,
            'daily_views': daily_views,
            'online_devices': online_devices,
            'total_unique_visitors': total_unique_visitors,
            'total_syncs': total_syncs
        }
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return {
            'views': 0,
            'daily_views': 0,
            'online_devices': 0,
            'total_unique_visitors': 0,
            'total_syncs': 0
        }

# Initialize database on startup
init_db()

# In-memory storage
content_by_ip = {}
last_update_by_ip = {}  # Track last update time for each IP
clients_by_ip = {}
analytics_lock = threading.Lock()

def get_client_ip():
    """Get client IP address"""
    return request.headers.get('X-Real-IP') or request.remote_addr

@app.before_request
def before_request():
    """Update analytics before each request"""
    try:
        if not request.path.startswith(('/static/', '/favicon.ico')):
            update_analytics(get_client_ip())
    except Exception as e:
        logger.error(f"Error in before_request: {str(e)}")

@app.route('/')
def index():
    """Render main page"""
    ip = get_client_ip()
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
        last_update_by_ip[ip] = datetime.now()
        return jsonify({'status': 'ok'})
    else:
        # Get all content for this IP's network
        network_content = {}
        current_time = datetime.now()
        
        for other_ip, content in content_by_ip.items():
            # Only include content from last 5 minutes
            if other_ip in last_update_by_ip:
                time_diff = (current_time - last_update_by_ip[other_ip]).total_seconds()
                if time_diff <= 300:  # 5 minutes
                    network_content[other_ip] = {
                        'content': content,
                        'length': len(content),
                        'last_update': last_update_by_ip[other_ip].isoformat()
                    }
        
        # Determine which content to return based on length and recency
        current_content = content_by_ip.get(ip, '')
        if network_content:
            # Sort by content length and recency
            sorted_content = sorted(
                network_content.items(),
                key=lambda x: (x[1]['length'], x[1]['last_update']),
                reverse=True
            )
            
            # If current content is shorter, use the longest content from network
            if len(current_content) < sorted_content[0][1]['length']:
                current_content = sorted_content[0][1]['content']
        
        return jsonify({
            'content': current_content,
            'network_content': network_content,
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

@app.route('/about')
def about():
    """Show about page"""
    try:
        analytics = get_analytics()
        current_time = datetime.now()
        
        # Get active networks (IPs with content in last 5 minutes)
        active_networks = 0
        for ip in content_by_ip:
            if ip in last_update_by_ip:
                time_diff = (current_time - last_update_by_ip[ip]).total_seconds()
                if time_diff <= 300:  # 5 minutes
                    active_networks += 1
        
        stats = {
            'total_pageviews': analytics['views'],
            'total_unique_visitors': analytics['total_unique_visitors'],
            'total_syncs': analytics['total_syncs'],
            'total_chars_shared': sum(len(content) for content in content_by_ip.values()),
            'active_networks': active_networks,
            'online_devices': analytics['online_devices']
        }
        return render_template('about.html', stats=stats, version=VERSION)
    except Exception as e:
        logger.error(f"About page error: {str(e)}")
        return str(e), 500

@app.route('/debug')
def debug():
    """Show debug information"""
    try:
        analytics = get_analytics()
        ip = get_client_ip()
        
        # Get active IPs and their content lengths
        active_ips = {}
        for ip_addr, content in content_by_ip.items():
            active_ips[ip_addr] = {
                'content_length': len(content),
                'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_current_ip': ip_addr == ip,
                'content_preview': content[:100] + '...' if len(content) > 100 else content
            }
        
        # Add the current IP if not in content_by_ip
        if ip not in active_ips:
            active_ips[ip] = {
                'content_length': 0,
                'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'is_current_ip': True,
                'content_preview': ''
            }
        
        system_info = {
            'python_version': sys.version.split()[0],
            'platform': sys.platform,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'current_ip': ip,
            'total_ips': len(content_by_ip),
            'total_content_size': sum(len(content) for content in content_by_ip.values()),
            'uptime': 'N/A'  # TODO: Add server uptime
        }
        
        # Get recent logs
        recent_logs = []
        if os.path.exists('logs/app.log'):
            with open('logs/app.log', 'r') as f:
                recent_logs = f.readlines()[-50:]  # Last 50 lines
        
        debug_info = {
            'analytics': analytics,
            'active_ips': active_ips,
            'system_info': system_info,
            'memory_usage': {
                'content_store': len(content_by_ip),
                'total_chars': sum(len(content) for content in content_by_ip.values())
            }
        }
        
        return render_template('debug.html', 
                            debug_info=debug_info,
                            analytics=analytics,
                            recent_logs=recent_logs,
                            version=VERSION)
    except Exception as e:
        logger.error(f"Debug page error: {str(e)}")
        return str(e), 500

if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 5050), app)
    print("Server starting on http://localhost:5050")
    server.serve_forever()
