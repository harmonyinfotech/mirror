from flask import Flask, render_template, request, jsonify, send_file
from datetime import datetime
import json
import os
import sys
import logging
import threading
from logging.handlers import RotatingFileHandler
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
import io
import qrcode
from PIL import Image

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

# In-memory storage
content_by_ip = {}
clients_by_ip = {}
analytics = {
    'views': 0,
    'unique_ips': set(),
    'daily_stats': {}
}
analytics_lock = threading.Lock()

def get_client_ip():
    """Get client IP address"""
    return request.headers.get('X-Real-IP') or request.remote_addr

def update_analytics(ip):
    """Update analytics data"""
    with analytics_lock:
        analytics['views'] += 1
        analytics['unique_ips'].add(ip)
        
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in analytics['daily_stats']:
            analytics['daily_stats'][today] = {
                'views': 0,
                'unique_ips': set()
            }
        analytics['daily_stats'][today]['views'] += 1
        analytics['daily_stats'][today]['unique_ips'].add(ip)

@app.route('/')
def index():
    """Render main page"""
    ip = get_client_ip()
    update_analytics(ip)
    return render_template('index.html', 
                         content=content_by_ip.get(ip, ''),
                         analytics=get_analytics())

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
        
        return render_template('debug.html',
                            system_info=system_info,
                            analytics=get_analytics(),
                            recent_logs=recent_logs)
    except Exception as e:
        logger.error(f"Debug page error: {str(e)}")
        return str(e), 500

def get_analytics():
    """Get analytics data"""
    with analytics_lock:
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in analytics['daily_stats']:
            analytics['daily_stats'][today] = {
                'views': 0,
                'unique_ips': set()
            }
        return {
            'views': analytics['views'],
            'unique_users': len(analytics['unique_ips']),
            'daily_views': analytics['daily_stats'][today]['views'],
            'daily_users': len(analytics['daily_stats'][today]['unique_ips'])
        }

@app.route('/ws')
def handle_websocket():
    """Handle WebSocket connections"""
    if request.environ.get('wsgi.websocket'):
        ws = request.environ['wsgi.websocket']
        ip = get_client_ip()
        
        try:
            # Initialize client list for this IP if needed
            if ip not in clients_by_ip:
                clients_by_ip[ip] = set()
            clients_by_ip[ip].add(ws)
            
            logger.info(f"Client connected from IP: {ip}")
            
            while True:
                message = ws.receive()
                if message is None:
                    break
                
                try:
                    data = json.loads(message)
                    content = data.get('content', '')
                    
                    # Update content for this IP
                    content_by_ip[ip] = content
                    
                    # Broadcast to all clients with same IP
                    dead_clients = set()
                    for client in clients_by_ip[ip]:
                        try:
                            if client != ws:  # Don't send back to sender
                                client.send(json.dumps({'content': content}))
                        except Exception:
                            dead_clients.add(client)
                    
                    # Clean up dead clients
                    for client in dead_clients:
                        clients_by_ip[ip].remove(client)
                    
                except json.JSONDecodeError:
                    logger.error(f"Invalid message format: {message}")
                
        except Exception as e:
            logger.error(f"WebSocket error: {str(e)}")
        finally:
            if ip in clients_by_ip:
                clients_by_ip[ip].discard(ws)
                if not clients_by_ip[ip]:
                    del clients_by_ip[ip]
                    if ip in content_by_ip:
                        del content_by_ip[ip]
            try:
                ws.close()
            except:
                pass
    return ''

if __name__ == '__main__':
    server = pywsgi.WSGIServer(('0.0.0.0', 5050), app, handler_class=WebSocketHandler)
    print("Server starting on http://localhost:5050")
    server.serve_forever()
