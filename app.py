"""
app.py - PneumoTrack Enterprise Hospital Management System
PostgreSQL-Optimized Flask Application for Railway Deployment

DESCRIPTION:
Complete hospital management system with all advanced features including
bed management, staff scheduling, patient flow, and real-time analytics.

AUTHOR: Hospital IT Team
VERSION: 4.0.0
LAST UPDATED: 2025
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from datetime import datetime, timedelta
from functools import wraps
from contextlib import contextmanager
from flask import Flask, request, jsonify, send_from_directory, current_app, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# =============================================================================
# CONFIGURATION CLASS FOR RAILWAY DEPLOYMENT
# =============================================================================
class RailwayConfig:
    """Configuration optimized for Railway deployment."""
    
    PORT = int(os.environ.get('PORT', 5000))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', '2000'))
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# =============================================================================
# DATABASE MANAGEMENT - POSTGRESQL OPTIMIZED
# =============================================================================
class DatabaseManager:
    """Advanced database management for PostgreSQL."""
    
    def __init__(self, app):
        self.app = app
    
    def get_connection(self):
        """Establish PostgreSQL database connection."""
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            raise Exception("DATABASE_URL environment variable not configured.")
        
        try:
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
        except Exception as e:
            current_app.logger.error(f"PostgreSQL connection failed: {e}")
            raise
    
    @contextmanager
    def get_cursor(self):
        """Context manager for database operations."""
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            yield cursor
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            current_app.logger.error(f"Database operation failed: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

# =============================================================================
# AUTO-DATABASE INITIALIZATION SYSTEM
# =============================================================================
def auto_initialize_database(app):
    """Automatic database setup for Railway PostgreSQL deployment."""
    app.logger.info("🔧 Starting automatic database initialization check...")
    
    try:
        db_manager = DatabaseManager(app)
        
        tables_exist = check_tables_exist(db_manager)
        
        if not tables_exist:
            app.logger.info("🚀 First deployment detected - creating database schema...")
            try:
                from schema import create_tables
                create_tables()
                app.logger.info("✅ Database schema created successfully")
            except Exception as e:
                app.logger.error(f"❌ Schema creation failed: {e}")
                raise
            
            try:
                from seeder import seed_data
                seed_data()
                app.logger.info("✅ Sample data seeded successfully")
            except Exception as e:
                app.logger.error(f"❌ Data seeding failed: {e}")
        else:
            if is_database_empty(db_manager):
                app.logger.info("📊 Database tables exist but no data - seeding...")
                try:
                    from seeder import seed_data
                    seed_data()
                    app.logger.info("✅ Sample data seeded successfully")
                except Exception as e:
                    app.logger.error(f"❌ Data seeding failed: {e}")
            else:
                app.logger.info("✅ Database already populated and ready")
                
    except Exception as e:
        app.logger.error(f"⚠️ Auto-initialization warning: {e}")

def check_tables_exist(db_manager):
    """Check if all required database tables exist."""
    try:
        with db_manager.get_cursor() as cursor:
            required_tables = [
                'hospital_system', 'department_units', 'medical_staff',
                'coverage_rules', 'guardia_schedules', 'enhanced_beds',
                'bed_audit_trail', 'patient_flow', 'medical_equipment',
                'daily_clinical_load', 'predictive_alerts', 'department_announcements'
            ]
            
            cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            existing_tables = [row['table_name'] for row in cursor.fetchall()]
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            return len(missing_tables) == 0
    except Exception as e:
        current_app.logger.error(f"❌ Error checking tables: {e}")
        return False

def is_database_empty(db_manager):
    """Check if database has any data in key tables."""
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
            staff_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            beds_count = cursor.fetchone()['count']
            
            return staff_count == 0 and beds_count == 0
    except Exception as e:
        current_app.logger.error(f"❌ Error checking database emptiness: {e}")
        return True

# =============================================================================
# API ROUTE HANDLERS - COMPLETE HOSPITAL MANAGEMENT SYSTEM
# =============================================================================
def get_medical_staff():
    """Retrieve all active medical staff with department information."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT ms.*, du.name as primary_unit_name
                FROM medical_staff ms
                LEFT JOIN department_units du ON ms.primary_unit_id = du.id
                WHERE ms.is_active = true
                ORDER BY ms.role, ms.last_name, ms.first_name
            """)
            staff = cursor.fetchall()
            return jsonify({"success": True, "staff": staff})
    except Exception as e:
        current_app.logger.error(f"Medical staff retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve medical staff"}), 500

def get_guardia_schedules():
    """Retrieve guardia schedules with filtering options."""
    try:
        date_filter = request.args.get('date')
        unit_id = request.args.get('unit_id', type=int)
        staff_id = request.args.get('staff_id', type=int)
        
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            query = """
                SELECT gs.*, 
                       ms.first_name || ' ' || ms.last_name as staff_name,
                       ms.role as staff_role,
                       du.name as unit_name,
                       du.code as unit_code
                FROM guardia_schedules gs
                JOIN medical_staff ms ON gs.staff_id = ms.id
                JOIN department_units du ON gs.unit_id = du.id
                WHERE 1=1
            """
            params = []
            
            if date_filter:
                query += " AND gs.schedule_date = %s"
                params.append(date_filter)
            if unit_id:
                query += " AND gs.unit_id = %s"
                params.append(unit_id)
            if staff_id:
                query += " AND gs.staff_id = %s"
                params.append(staff_id)
            
            query += " ORDER BY gs.schedule_date, gs.shift_type, du.name"
            
            cursor.execute(query, params)
            schedules = cursor.fetchall()
            
            return jsonify({"success": True, "schedules": schedules})
    except Exception as e:
        current_app.logger.error(f"Guardia schedules retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve schedules"}), 500

def get_enhanced_beds():
    """Retrieve enhanced bed management data with patient information."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    eb.*,
                    pf.patient_code,
                    pf.acuity_level,
                    pf.primary_diagnosis,
                    ms.first_name || ' ' || ms.last_name as attending_doctor
                FROM enhanced_beds eb
                LEFT JOIN patient_flow pf ON eb.patient_id = pf.id
                LEFT JOIN medical_staff ms ON pf.attending_doctor_id = ms.id
                ORDER BY eb.room_code, eb.bed_number
            """)
            beds = cursor.fetchall()
            
            total_beds = len(beds)
            occupied_beds = len([bed for bed in beds if bed['status'] == 'occupied'])
            available_beds = len([bed for bed in beds if bed['status'] == 'empty'])
            
            stats = {
                'total_beds': total_beds,
                'occupied_beds': occupied_beds,
                'available_beds': available_beds,
                'occupancy_rate': round((occupied_beds / total_beds) * 100, 1) if total_beds > 0 else 0
            }
            
            return jsonify({
                "success": True, 
                "beds": beds,
                "statistics": stats
            })
    except Exception as e:
        current_app.logger.error(f"Enhanced beds retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve bed data"}), 500

def get_department_units():
    """Retrieve all active department units."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM department_units 
                WHERE is_active = true 
                ORDER BY name
            """)
            units = cursor.fetchall()
            return jsonify({"success": True, "units": units})
    except Exception as e:
        current_app.logger.error(f"Department units retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve department units"}), 500

def get_patient_flow():
    """Retrieve current patient flow with bed assignments."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    pf.*,
                    eb.room_code,
                    eb.bed_number,
                    du.name as unit_name,
                    ms.first_name || ' ' || ms.last_name as doctor_name
                FROM patient_flow pf
                LEFT JOIN enhanced_beds eb ON pf.current_bed_id = eb.id
                LEFT JOIN department_units du ON pf.current_unit_id = du.id
                LEFT JOIN medical_staff ms ON pf.attending_doctor_id = ms.id
                WHERE pf.current_status = 'admitted'
                ORDER BY pf.acuity_level DESC, pf.admission_datetime
            """)
            patients = cursor.fetchall()
            return jsonify({"success": True, "patients": patients})
    except Exception as e:
        current_app.logger.error(f"Patient flow retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve patient flow"}), 500

def get_system_overview():
    """Get comprehensive system overview with key performance metrics."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            metrics = {}
            
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_active = true")
            metrics['total_staff'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_on_call = true")
            metrics['on_call_staff'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            metrics['total_beds'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
            metrics['occupied_beds'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM patient_flow WHERE current_status = 'admitted'")
            metrics['active_patients'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM patient_flow WHERE acuity_level = 'critical'")
            metrics['critical_patients'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM guardia_schedules WHERE schedule_date = CURRENT_DATE")
            metrics['today_schedules'] = cursor.fetchone()['count']
            
            metrics['occupancy_rate'] = round(
                (metrics['occupied_beds'] / metrics['total_beds']) * 100, 1
            ) if metrics['total_beds'] > 0 else 0
            
            return jsonify({
                "success": True,
                "overview": metrics,
                "timestamp": datetime.now().isoformat(),
                "system_health": "healthy"
            })
    except Exception as e:
        current_app.logger.error(f"System overview retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve system overview"}), 500

def get_system_status():
    """System status endpoint for frontend health checks."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            total_beds = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
            occupied_beds = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_active = true")
            total_staff = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM patient_flow WHERE current_status = 'admitted'")
            active_patients = cursor.fetchone()['count']
            
        return jsonify({
            "success": True,
            "status": "operational",
            "system_health": "healthy",
            "beds_available": total_beds - occupied_beds,
            "beds_total": total_beds,
            "staff_available": total_staff,
            "patients_active": active_patients,
            "last_updated": datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f"System status error: {e}")
        return jsonify({"success": False, "error": "Failed to get system status"}), 500

def get_equipment():
    """Retrieve medical equipment inventory."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT * FROM medical_equipment ORDER BY equipment_type, status")
            equipment = cursor.fetchall()
            return jsonify({"success": True, "equipment": equipment})
    except Exception as e:
        current_app.logger.error(f"Equipment retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve equipment"}), 500

def get_intelligent_alerts():
    """Retrieve active intelligent alerts."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM predictive_alerts 
                WHERE resolved = false 
                ORDER BY severity DESC, triggered_at DESC
            """)
            alerts = cursor.fetchall()
            return jsonify({"success": True, "alerts": alerts})
    except Exception as e:
        current_app.logger.error(f"Alerts retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve alerts"}), 500

def get_analytics_dashboard():
    """Retrieve analytics dashboard data."""
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
            occupied_beds = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            total_beds = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM patient_flow WHERE acuity_level = 'critical'")
            critical_patients = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_on_call = true")
            on_call_staff = cursor.fetchone()['count']
            
            return jsonify({
                "success": True,
                "analytics": {
                    "occupancy_rate": round((occupied_beds / total_beds) * 100, 1) if total_beds > 0 else 0,
                    "critical_patients": critical_patients,
                    "on_call_staff": on_call_staff,
                    "total_beds": total_beds,
                    "occupied_beds": occupied_beds
                }
            })
    except Exception as e:
        current_app.logger.error(f"Analytics dashboard error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve analytics"}), 500

# =============================================================================
# APPLICATION FACTORY AND ROUTE REGISTRATION
# =============================================================================
def create_app(config_class=RailwayConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Security middleware
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    
    Talisman(
        app,
        content_security_policy=None,
        force_https=os.environ.get('RAILWAY_ENVIRONMENT') == 'production',
        strict_transport_security=True
    )
    
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{config_class.RATE_LIMIT_PER_HOUR}/hour"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    
    # Logging
    logging.basicConfig(
        level=logging.INFO if os.environ.get('RAILWAY_ENVIRONMENT') == 'production' else logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s [%(name)s:%(lineno)d]'
    )
    app.logger.setLevel(logging.INFO)
    
    # Database initialization
    with app.app_context():
        app.logger.info("🚀 Starting application with PostgreSQL database...")
        auto_initialize_database(app)
    
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
            "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'development'),
            "timestamp": datetime.now().isoformat(),
            "version": "4.0.0"
        })
    
    # Core API endpoints
    @app.route('/api/medical-staff')
    def medical_staff():
        return get_medical_staff()
    
    @app.route('/api/staff')
    def staff_compat():
        return get_medical_staff()
    
    @app.route('/api/guardia-schedules')
    def guardia_schedules():
        return get_guardia_schedules()
    
    @app.route('/api/guardia/schedule')
    def guardia_schedule_compat():
        return get_guardia_schedules()
    
    @app.route('/api/enhanced-beds')
    def enhanced_beds():
        return get_enhanced_beds()
    
    @app.route('/api/beds')
    def beds_compat():
        return get_enhanced_beds()
    
    @app.route('/api/department-units')
    def department_units():
        return get_department_units()
    
    @app.route('/api/units')
    def units_compat():
        return get_department_units()
    
    @app.route('/api/patient-flow')
    def patient_flow():
        return get_patient_flow()
    
    @app.route('/api/system-overview')
    def system_overview():
        return get_system_overview()
    
    # Additional endpoints
    @app.route('/api/system/status')
    def system_status():
        return get_system_status()
    
    @app.route('/api/equipment')
    def equipment():
        return get_equipment()
    
    @app.route('/api/alerts/intelligent')
    def intelligent_alerts():
        return get_intelligent_alerts()
    
    @app.route('/api/analytics/dashboard')
    def analytics_dashboard():
        return get_analytics_dashboard()
    
    # Admin endpoints
    @app.route('/api/admin/initialize-database', methods=['POST'])
    def manual_initialize_database():
        try:
            app.logger.info("🛠️ Manual database initialization triggered via API")
            auto_initialize_database(app)
            return jsonify({
                "success": True,
                "message": "Database initialization completed",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/debug/database')
    def debug_database():
        try:
            db_manager = DatabaseManager(app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = [row['table_name'] for row in cursor.fetchall()]
                
                cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
                staff_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
                beds_count = cursor.fetchone()['count']
                
            return jsonify({
                "success": True,
                "database_status": {
                    "tables_exist": len(tables) > 0,
                    "tables_found": tables,
                    "staff_count": staff_count,
                    "beds_count": beds_count,
                    "database_url_configured": bool(os.environ.get('DATABASE_URL'))
                }
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    
    # Request logging
    @app.before_request
    def log_request_info():
        if request.endpoint and request.endpoint != 'static':
            app.logger.info(f"{request.method} {request.path} - IP: {request.remote_addr}")
    
    return app

# =============================================================================
# APPLICATION STARTUP
# =============================================================================
app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('RAILWAY_ENVIRONMENT') != 'production'
    
    app.logger.info(f"🚀 Starting PneumoTrack Enterprise on port {port}")
    app.logger.info(f"🏥 Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}")
    
    app.run(host='0.0.0.0', port=port, debug=debug, threaded=True)