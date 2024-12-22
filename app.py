from flask import Flask, render_template, request, jsonify
from datetime import datetime, timedelta
import json
import requests
import ipaddress
from collections import defaultdict
from version import VERSION, CHANGELOG

app = Flask(__name__)

# In-memory storage for shared content and analytics
shared_content = {}
analytics = {
    'total_visits': 0,
    'total_syncs': 0,
    'total_chars_shared': 0,
    'daily_stats': defaultdict(lambda: {
        'visits': 0,
        'syncs': 0,
        'chars': 0
    }),
    'active_networks': set()  # Track unique networks
}

class ContentVersion:
    def __init__(self, content='', version=0):
        self.content = content
        self.version = version
        self.last_updated = datetime.now()
        self.files = []

def clean_old_content():
    """Remove content older than 24 hours"""
    current_time = datetime.now()
    to_remove = []
    for ip, data in shared_content.items():
        if current_time - data.last_updated > timedelta(hours=24):
            to_remove.append(ip)
    for ip in to_remove:
        del shared_content[ip]

def update_analytics(network, chars=0, is_sync=False):
    """Update analytics data"""
    today = datetime.now().strftime('%Y-%m-%d')
    analytics['total_visits'] += 1
    analytics['daily_stats'][today]['visits'] += 1
    analytics['active_networks'].add(network)
    
    if is_sync:
        analytics['total_syncs'] += 1
        analytics['daily_stats'][today]['syncs'] += 1
    
    if chars > 0:
        analytics['total_chars_shared'] += chars
        analytics['daily_stats'][today]['chars'] += chars

def get_analytics():
    """Get formatted analytics data"""
    today = datetime.now().strftime('%Y-%m-%d')
    return {
        'total_visits': analytics['total_visits'],
        'total_syncs': analytics['total_syncs'],
        'total_chars_shared': analytics['total_chars_shared'],
        'today_visits': analytics['daily_stats'][today]['visits'],
        'today_syncs': analytics['daily_stats'][today]['syncs'],
        'today_chars': analytics['daily_stats'][today]['chars'],
        'active_networks': len(analytics['active_networks'])
    }

def get_public_ip():
    """Get both IPv4 and IPv6 addresses and return the appropriate one"""
    try:
        # Try IPv6 first
        response = requests.get('https://api64.ipify.org')
        if response.status_code == 200:
            ip = response.text.strip()
            # Verify if it's a valid IPv6
            try:
                ipaddress.IPv6Address(ip)
                print(f"Using IPv6: {ip}")
                return ip
            except ipaddress.AddressValueError:
                pass
    except:
        pass

    try:
        # Fallback to IPv4
        response = requests.get('https://api.ipify.org')
        if response.status_code == 200:
            ip = response.text.strip()
            try:
                ipaddress.IPv4Address(ip)
                print(f"Using IPv4: {ip}")
                return ip
            except ipaddress.AddressValueError:
                pass
    except:
        pass
    
    # Final fallback to local detection
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0]
    return request.remote_addr

def get_ip_network(ip):
    """Convert IP address to network address for grouping"""
    try:
        # For IPv6, group by /64 network
        if ':' in ip:
            return str(ipaddress.IPv6Network(f"{ip}/64", strict=False).network_address)
        # For IPv4, group by /24 network
        else:
            return str(ipaddress.IPv4Network(f"{ip}/24", strict=False).network_address)
    except:
        return ip

@app.route('/')
def index():
    ip = get_public_ip()
    network = get_ip_network(ip)
    update_analytics(network)
    stats = get_analytics()
    return render_template('index.html', stats=stats)

@app.route('/api/content', methods=['GET', 'POST'])
def handle_content():
    ip = get_public_ip()
    network = get_ip_network(ip)
    print(f"IP: {ip}, Network: {network}, Method: {request.method}")
    
    if request.method == 'POST':
        content = request.json.get('content', '')
        client_version = request.json.get('version', 0)
        
        if network not in shared_content:
            shared_content[network] = ContentVersion()
        
        # Only update if the client version is newer or equal
        if client_version >= shared_content[network].version:
            shared_content[network].content = content
            shared_content[network].version = client_version + 1
            shared_content[network].last_updated = datetime.now()
            clean_old_content()
            update_analytics(network, len(content), True)
            print(f"Saved content v{shared_content[network].version} for network {network}: {content[:50]}...")
            return jsonify({
                'status': 'success',
                'version': shared_content[network].version
            })
        else:
            # Client is behind, send current version
            return jsonify({
                'status': 'outdated',
                'content': shared_content[network].content,
                'version': shared_content[network].version
            })
    
    elif request.method == 'GET':
        client_version = request.args.get('version', type=int, default=0)
        if network in shared_content:
            content_obj = shared_content[network]
            # Only send content if there's a newer version
            if content_obj.version > client_version:
                return jsonify({
                    'content': content_obj.content,
                    'version': content_obj.version,
                    'has_update': True
                })
            return jsonify({
                'has_update': False,
                'version': content_obj.version
            })
        return jsonify({
            'content': '',
            'version': 0,
            'has_update': False
        })

@app.route('/about')
def about():
    stats = get_analytics()
    return render_template('about.html', stats=stats, version=VERSION, changelog=CHANGELOG)

@app.route('/api/stats')
def stats():
    return jsonify(get_analytics())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
