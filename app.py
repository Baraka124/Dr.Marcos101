"""
COMPLETE HOSPITAL MANAGEMENT SYSTEM
With manual database initialization
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
    try:
        # Try DATABASE_URL first
        database_url = os.environ.get('DATABASE_URL')
        if database_url:
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
        
        # Fallback to direct connection
        conn = psycopg2.connect(
            database='railway',
            user='postgres',
            password='AOQxwQrpYKTcWKGlSMxWFtabJpwXbJvC',
            host='postgres.railway.internal',
            port=5432,
            sslmode='require',
            cursor_factory=RealDictCursor
        )
        return conn
        
    except Exception as e:
        raise Exception(f"Database connection failed: {e}")

def initialize_database():
    """Database initialization - creates tables and seeds data"""
    print("🔄 Initializing database...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create medical_staff table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medical_staff (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                role VARCHAR(50),
                is_active BOOLEAN DEFAULT true
            )
        """)
        print("✅ medical_staff table created")
        
        # Create enhanced_beds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enhanced_beds (
                id SERIAL PRIMARY KEY,
                room_code VARCHAR(20),
                bed_number VARCHAR(10),
                status VARCHAR(20) DEFAULT 'empty'
            )
        """)
        print("✅ enhanced_beds table created")
        
        # Check if data exists
        cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
        staff_count = cursor.fetchone()['count']
        
        if staff_count == 0:
            # Seed sample data
            cursor.execute("INSERT INTO medical_staff (first_name, last_name, role) VALUES ('Dr. Maria', 'Gonzalez', 'Doctor')")
            cursor.execute("INSERT INTO medical_staff (first_name, last_name, role) VALUES ('Nurse Carlos', 'Rodriguez', 'Nurse')")
            cursor.execute("INSERT INTO medical_staff (first_name, last_name, role) VALUES ('Dr. Ana', 'Martinez', 'Surgeon')")
            
            cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number, status) VALUES ('ER-101', 'A', 'empty')")
            cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number, status) VALUES ('ER-102', 'B', 'occupied')")
            cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number, status) VALUES ('ICU-201', '1', 'empty')")
            
            print("✅ Sample data seeded")
        else:
            print("✅ Data already exists")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
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
        "version": "4.0.0"
    })

# Manual initialization endpoint
@app.route('/api/admin/init', methods=['POST', 'GET'])
def manual_init():
    """Manual endpoint to force database initialization"""
    global database_initialized
    try:
        print("🛠️ Manual database initialization triggered")
        result = initialize_database()
        database_initialized = True
        return jsonify({
            "success": True,
            "message": "Database initialization completed",
            "initialized": result,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Simple staff endpoint
@app.route('/api/staff')
def get_staff():
    global database_initialized
    if not database_initialized:
        # Auto-initialize on first API call
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
        # Auto-initialize on first API call
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
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row['table_name'] for row in cursor.fetchall()]
        
        # Try to count staff (will fail if table doesn't exist)
        staff_count = 0
        if 'medical_staff' in tables:
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
            staff_count = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "database_connected": True,
            "tables_found": tables,
            "staff_count": staff_count,
            "needs_initialization": staff_count == 0
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