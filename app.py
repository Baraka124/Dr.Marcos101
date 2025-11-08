"""
COMPLETE HOSPITAL MANAGEMENT SYSTEM
With all frontend-compatible API endpoints
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
                specialty VARCHAR(100),
                is_active BOOLEAN DEFAULT true,
                is_on_call BOOLEAN DEFAULT false,
                current_status VARCHAR(20) DEFAULT 'available'
            )
        """)
        print("✅ medical_staff table created")
        
        # Create enhanced_beds table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enhanced_beds (
                id SERIAL PRIMARY KEY,
                room_code VARCHAR(20),
                bed_number VARCHAR(10),
                status VARCHAR(20) DEFAULT 'empty',
                patient_id INTEGER,
                unit_id INTEGER
            )
        """)
        print("✅ enhanced_beds table created")
        
        # Create department_units table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS department_units (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                code VARCHAR(20),
                specialty VARCHAR(100),
                capacity INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT true
            )
        """)
        print("✅ department_units table created")
        
        # Create additional tables for frontend compatibility
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medical_equipment (
                id SERIAL PRIMARY KEY,
                equipment_type VARCHAR(100),
                status VARCHAR(20),
                location VARCHAR(100)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictive_alerts (
                id SERIAL PRIMARY KEY,
                alert_type VARCHAR(100),
                severity VARCHAR(20),
                message TEXT,
                resolved BOOLEAN DEFAULT false
            )
        """)
        
        # Check if data exists
        cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
        staff_count = cursor.fetchone()['count']
        
        if staff_count == 0:
            # Seed sample data
            cursor.execute("INSERT INTO medical_staff (first_name, last_name, role, specialty) VALUES ('Dr. Maria', 'Gonzalez', 'Doctor', 'Emergency Medicine')")
            cursor.execute("INSERT INTO medical_staff (first_name, last_name, role, specialty) VALUES ('Nurse Carlos', 'Rodriguez', 'Nurse', 'Emergency Medicine')")
            cursor.execute("INSERT INTO medical_staff (first_name, last_name, role, specialty) VALUES ('Dr. Ana', 'Martinez', 'Surgeon', 'Surgery')")
            
            cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number, status) VALUES ('ER-101', 'A', 'empty')")
            cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number, status) VALUES ('ER-102', 'B', 'occupied')")
            cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number, status) VALUES ('ICU-201', '1', 'empty')")
            
            cursor.execute("INSERT INTO department_units (name, code, specialty, capacity) VALUES ('Emergency Room', 'ER', 'Emergency Medicine', 30)")
            cursor.execute("INSERT INTO department_units (name, code, specialty, capacity) VALUES ('Intensive Care Unit', 'ICU', 'Critical Care', 20)")
            cursor.execute("INSERT INTO department_units (name, code, specialty, capacity) VALUES ('Cardiology', 'CARD', 'Cardiology', 25)")
            
            cursor.execute("INSERT INTO medical_equipment (equipment_type, status, location) VALUES ('Ventilator', 'available', 'ICU')")
            cursor.execute("INSERT INTO medical_equipment (equipment_type, status, location) VALUES ('Defibrillator', 'in_use', 'ER')")
            
            cursor.execute("INSERT INTO predictive_alerts (alert_type, severity, message) VALUES ('Staff Shortage', 'medium', 'ER staff below recommended levels')")
            
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

# =============================================================================
# ALL FRONTEND API ENDPOINTS
# =============================================================================

# System Status
@app.route('/api/system/status')
def system_status():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
        total_beds = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
        occupied_beds = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_active = true")
        total_staff = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "status": "operational",
            "system_health": "healthy",
            "beds_available": total_beds - occupied_beds,
            "beds_total": total_beds,
            "staff_available": total_staff,
            "patients_active": occupied_beds,
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Department Units
@app.route('/api/units')
def department_units():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM department_units WHERE is_active = true ORDER BY name")
        units = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "units": units})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Medical Staff
@app.route('/api/medical-staff')
def medical_staff():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_staff WHERE is_active = true ORDER BY role, last_name")
        staff = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "staff": staff})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/staff')
def staff_compat():
    return medical_staff()

# Beds
@app.route('/api/enhanced-beds')
def enhanced_beds():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM enhanced_beds ORDER BY room_code, bed_number")
        beds = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "beds": beds})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/beds')
def beds_compat():
    return enhanced_beds()

# Equipment
@app.route('/api/equipment')
def equipment():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM medical_equipment ORDER BY equipment_type, status")
        equipment = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "equipment": equipment})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Alerts
@app.route('/api/alerts/intelligent')
def intelligent_alerts():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM predictive_alerts WHERE resolved = false ORDER BY severity DESC")
        alerts = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "alerts": alerts})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Announcements
@app.route('/api/announcements')
def announcements():
    # Return empty array for now
    return jsonify({"success": True, "announcements": []})

# Guardia Schedule
@app.route('/api/guardia/schedule')
def guardia_schedule():
    # Return empty array for now
    return jsonify({"success": True, "schedules": []})

# Clinical Load
@app.route('/api/clinical/load')
def clinical_load():
    # Return empty array for now
    return jsonify({"success": True, "clinical_load": []})

# Absence Requests
@app.route('/api/absence/requests')
def absence_requests():
    # Return empty array for now
    return jsonify({"success": True, "absences": []})

# Analytics Dashboard
@app.route('/api/analytics/dashboard')
def analytics_dashboard():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
        occupied_beds = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
        total_beds = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_on_call = true")
        on_call_staff = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "analytics": {
                "occupancy_rate": round((occupied_beds / total_beds) * 100, 1) if total_beds > 0 else 0,
                "on_call_staff": on_call_staff,
                "total_beds": total_beds,
                "occupied_beds": occupied_beds
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Staff Availability
@app.route('/api/staff/availability')
def staff_availability():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, first_name, last_name, role, current_status, is_on_call 
            FROM medical_staff 
            WHERE is_active = true 
            ORDER BY role, last_name
        """)
        availability = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "availability": availability})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Dashboard Summary
@app.route('/api/dashboard/summary')
def dashboard_summary():
    return system_overview()

# System Overview
@app.route('/api/system-overview')
def system_overview():
    global database_initialized
    if not database_initialized:
        initialize_database()
        database_initialized = True
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_active = true")
        staff_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_on_call = true")
        on_call_staff = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
        beds_count = cursor.fetchone()['count']
        
        cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
        occupied_beds = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "overview": {
                "total_staff": staff_count,
                "on_call_staff": on_call_staff,
                "total_beds": beds_count,
                "occupied_beds": occupied_beds,
                "occupancy_rate": round((occupied_beds / beds_count) * 100, 1) if beds_count > 0 else 0
            },
            "timestamp": datetime.now().isoformat(),
            "system_health": "healthy"
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Debug endpoint
@app.route('/api/debug/database')
def debug_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        tables = [row['table_name'] for row in cursor.fetchall()]
        
        # Check data counts
        staff_count = 0
        beds_count = 0
        if 'medical_staff' in tables:
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
            staff_count = cursor.fetchone()['count']
        
        if 'enhanced_beds' in tables:
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            beds_count = cursor.fetchone()['count']
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "database_status": {
                "tables_exist": len(tables) > 0,
                "tables_found": tables,
                "staff_count": staff_count,
                "beds_count": beds_count,
                "needs_initialization": staff_count == 0
            }
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "database_status": "error"
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting Hospital Management System on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)