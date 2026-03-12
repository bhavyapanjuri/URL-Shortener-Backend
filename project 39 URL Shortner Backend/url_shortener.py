from flask import Flask, request, jsonify, redirect
from datetime import datetime, timedelta
import string
import random
import time
from collections import defaultdict

app = Flask(__name__)

# In-memory storage
url_db = {}
analytics_db = defaultdict(lambda: {"clicks": 0, "last_access": []})
rate_limit_db = defaultdict(list)

# Configuration
BASE_URL = "http://short.ly/"
RATE_LIMIT = 10  # requests per minute
SHORT_CODE_LENGTH = 6

def generate_short_code():
    """Generate unique short code using random alphanumeric characters"""
    chars = string.ascii_letters + string.digits
    while True:
        code = ''.join(random.choices(chars, k=SHORT_CODE_LENGTH))
        if code not in url_db:
            return code

def check_rate_limit(ip):
    """Check if IP has exceeded rate limit"""
    current_time = time.time()
    rate_limit_db[ip] = [t for t in rate_limit_db[ip] if current_time - t < 60]
    
    if len(rate_limit_db[ip]) >= RATE_LIMIT:
        return False
    
    rate_limit_db[ip].append(current_time)
    return True

def is_expired(expiry_date):
    """Check if URL has expired"""
    if expiry_date and datetime.now() > expiry_date:
        return True
    return False

@app.route('/shorten', methods=['POST'])
def shorten_url():
    """Create short URL from long URL"""
    ip = request.remote_addr
    
    # Rate limiting
    if not check_rate_limit(ip):
        return jsonify({"error": "Rate limit exceeded. Try again later."}), 429
    
    data = request.get_json()
    long_url = data.get('url')
    expiry_days = data.get('expiry_days', None)
    
    # Validation
    if not long_url or not long_url.startswith(('http://', 'https://')):
        return jsonify({"error": "Invalid URL format"}), 400
    
    # Check for duplicate
    for code, info in url_db.items():
        if info['long_url'] == long_url and not is_expired(info['expiry']):
            return jsonify({
                "short_url": BASE_URL + code,
                "short_code": code,
                "message": "URL already exists"
            }), 200
    
    # Generate short code
    short_code = generate_short_code()
    
    # Calculate expiry
    expiry = None
    if expiry_days:
        expiry = datetime.now() + timedelta(days=expiry_days)
    
    # Store mapping
    url_db[short_code] = {
        "long_url": long_url,
        "created_at": datetime.now(),
        "expiry": expiry
    }
    
    return jsonify({
        "short_url": BASE_URL + short_code,
        "short_code": short_code,
        "long_url": long_url,
        "created_at": url_db[short_code]['created_at'].isoformat(),
        "expiry": expiry.isoformat() if expiry else None
    }), 201

@app.route('/<short_code>', methods=['GET'])
def redirect_url(short_code):
    """Redirect short URL to original long URL"""
    # Check if short code exists
    if short_code not in url_db:
        return jsonify({"error": "Short URL not found"}), 404
    
    url_info = url_db[short_code]
    
    # Check expiry
    if is_expired(url_info['expiry']):
        return jsonify({"error": "This link has expired"}), 410
    
    # Update analytics
    analytics_db[short_code]["clicks"] += 1
    analytics_db[short_code]["last_access"].append(datetime.now().isoformat())
    
    # Redirect
    return redirect(url_info['long_url'], code=302)

@app.route('/analytics/<short_code>', methods=['GET'])
def get_analytics(short_code):
    """Get analytics for a short URL"""
    if short_code not in url_db:
        return jsonify({"error": "Short URL not found"}), 404
    
    url_info = url_db[short_code]
    analytics = analytics_db[short_code]
    
    return jsonify({
        "short_code": short_code,
        "long_url": url_info['long_url'],
        "created_at": url_info['created_at'].isoformat(),
        "expiry": url_info['expiry'].isoformat() if url_info['expiry'] else None,
        "total_clicks": analytics['clicks'],
        "recent_access": analytics['last_access'][-10:]  # Last 10 accesses
    }), 200

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get overall system statistics"""
    total_urls = len(url_db)
    active_urls = sum(1 for info in url_db.values() if not is_expired(info['expiry']))
    expired_urls = total_urls - active_urls
    total_clicks = sum(analytics['clicks'] for analytics in analytics_db.values())
    
    return jsonify({
        "total_urls": total_urls,
        "active_urls": active_urls,
        "expired_urls": expired_urls,
        "total_clicks": total_clicks
    }), 200

if __name__ == '__main__':
    print("=" * 60)
    print("URL Shortener Backend - Running")
    print("=" * 60)
    print("\nEndpoints:")
    print("  POST   /shorten              - Create short URL")
    print("  GET    /<short_code>         - Redirect to long URL")
    print("  GET    /analytics/<code>     - Get URL analytics")
    print("  GET    /stats                - Get system stats")
    print("\nFeatures:")
    print("  ✓ Short ↔ Long URL mapping")
    print("  ✓ Link expiration support")
    print("  ✓ Rate limiting (10 req/min)")
    print("  ✓ Click analytics tracking")
    print("=" * 60)
    app.run(debug=True, port=5000)


#pip install flask
#python url_shortener.py
