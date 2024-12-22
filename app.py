from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
import requests

app = Flask(__name__)

# In-memory storage for shared content
# Structure: {ip_address: {'content': str, 'files': [], 'last_updated': datetime}}
shared_content = {}

def clean_old_content():
    """Remove content older than 24 hours"""
    current_time = datetime.now()
    to_remove = []
    for ip, data in shared_content.items():
        if current_time - data['last_updated'] > timedelta(hours=24):
            to_remove.append(ip)
    for ip in to_remove:
        del shared_content[ip]

def get_public_ip():
    """Get the real public IP address"""
    try:
        response = requests.get('https://api.ipify.org', timeout=2)
        if response.status_code == 200:
            return response.text.strip()
    except:
        # Fallback to local detection only if ipify is unreachable
        if request.headers.get('X-Forwarded-For'):
            return request.headers.get('X-Forwarded-For').split(',')[0]
        return request.remote_addr

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/content', methods=['GET', 'POST'])
def handle_content():
    ip = get_public_ip()
    print(f"Public IP: {ip}, Method: {request.method}")
    
    if request.method == 'POST':
        content = request.json.get('content', '')
        if ip not in shared_content:
            shared_content[ip] = {'content': '', 'files': [], 'last_updated': datetime.now()}
        shared_content[ip]['content'] = content
        shared_content[ip]['last_updated'] = datetime.now()
        clean_old_content()
        print(f"Saved content for IP {ip}: {content[:50]}...")
        return jsonify({'status': 'success'})
    
    elif request.method == 'GET':
        if ip in shared_content:
            content = shared_content[ip]['content']
            print(f"Retrieved content for IP {ip}: {content[:50]}...")
            return jsonify({
                'content': content,
                'files': shared_content[ip]['files']
            })
        return jsonify({'content': '', 'files': []})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
