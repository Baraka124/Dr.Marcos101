"""
MINIMAL WORKING Hospital Management System
WITH DELAYED DATABASE INITIALIZATION
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from datetime import datetime
from flask import Flask, jsonify, render_template, send_from_directory

app = Flask(__name__, template_folder='templates')

# Basic configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key')

def get_db_connection():
    """Get PostgreSQL database connection"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL not configured")
    
    result = urlparse(database_url)
    conn = psycopg2.connect(
        database=result.path[1:],
        user=result.username,
        password=result.password,
        host=result.hostname,
        port=result.port,
        sslmode='require',
        cursor_factory=RealDictCursor
    )
    return conn

def initialize_database():
    """Database initialization - called on first API request"""
    print("🔄 Initializing database...")
    try:
        # Try to create tables
        from schema import create_tables
        create_tables()
        print("✅ Tables created")
        
        # Try to seed data
        from seeder import seed_data  
        seed_data()
        print("✅ Data seeded")
        return True
    except Exception as e:
        print(f"⚠️ Init warning: {e}")
        return False

# Track initialization
database_initialized = False

# Frontend routes
@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/beds')
def serve_beds():
    return render_template('beds.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

# Health check
@app.route('/api/health')
def health_check():
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

# Simple staff endpoint
@app.route('/api/staff')
def get_staff():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_staff LIMIT 10")
        staff = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "staff": staff})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Simple beds endpoint  
@app.route('/api/beds')
def get_beds():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM enhanced_beds LIMIT 10")
        beds = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "beds": beds})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Debug endpoint
@app.route('/api/debug')
def debug_info():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row['table_name'] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "database_connected": True,
            "tables_found": tables,
            "database_url_set": bool(os.environ.get('DATABASE_URL'))
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "database_connected": False
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)