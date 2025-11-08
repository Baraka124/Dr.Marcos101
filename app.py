"""
app.py - PneumoTrack Enterprise Hospital Management System
PostgreSQL-Optimized Flask Application for Railway Deployment
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, current_app, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman

# =============================================================================
# CONFIGURATION CLASS FOR RAILWAY DEPLOYMENT
# =============================================================================
class RailwayConfig:
    PORT = int(os.environ.get('PORT', 5000))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', '2000'))
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

# =============================================================================
# DATABASE MANAGEMENT - POSTGRESQL OPTIMIZED
# =============================================================================
class DatabaseManager:
    def __init__(self, app):
        self.app = app
    
    def get_connection(self):
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            raise Exception("DATABASE_URL environment variable not configured. Please add PostgreSQL database to Railway.")
        
        try:
            # Parse the database URL for PostgreSQL
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
    
    def get_cursor(self):
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
    app.logger.info("🔧 Starting automatic database initialization check...")
    
    try:
        db_manager = DatabaseManager(app)
        
        # Check if database tables exist
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
            
            if missing_tables:
                current_app.logger.warning(f"⚠️ Missing tables: {missing_tables}")
                return False
            else:
                current_app.logger.info("✅ All required tables exist")
                return True
    except Exception as e:
        current_app.logger.error(f"❌ Error checking tables: {e}")
        return False

def is_database_empty(db_manager):
    try:
        with db_manager.get_cursor() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
            staff_count = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            beds_count = cursor.fetchone()['count']
            
            is_empty = staff_count == 0 and beds_count == 0
            current_app.logger.info(f"📊 Database emptiness check - Staff: {staff_count}, Beds: {beds_count}")
            
            return is_empty
    except Exception as e:
        current_app.logger.error(f"❌ Error checking database emptiness: {e}")
        return True

# =============================================================================
# APPLICATION FACTORY
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
    
    # Routes
    @app.route('/')
    def serve_index():
        return render_template('index.html')

    @app.route('/beds')
    def serve_beds():
        return render_template('beds.html')

    @app.route('/static/<path:path>')
    def serve_static(path):
        return send_from_directory('static', path)
    
    @app.route('/<path:path>')
    def serve_all_static(path):
        return send_from_directory('.', path)
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            "status": "healthy",
            "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'development'),
            "timestamp": datetime.now().isoformat(),
            "version": "4.0.0"
        })
    
    # API endpoints
    @app.route('/api/medical-staff')
    def medical_staff():
        try:
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT * FROM medical_staff WHERE is_active = true ORDER BY role, last_name")
                staff = cursor.fetchall()
                return jsonify({"success": True, "staff": staff})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/staff')
    def staff_compat():
        return medical_staff()
    
    @app.route('/api/enhanced-beds')
    def enhanced_beds():
        try:
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT * FROM enhanced_beds ORDER BY room_code, bed_number")
                beds = cursor.fetchall()
                return jsonify({"success": True, "beds": beds})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/beds')
    def beds_compat():
        return enhanced_beds()
    
    @app.route('/api/department-units')
    def department_units():
        try:
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT * FROM department_units WHERE is_active = true ORDER BY name")
                units = cursor.fetchall()
                return jsonify({"success": True, "units": units})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    @app.route('/api/units')
    def units_compat():
        return department_units()
    
    @app.route('/api/system-overview')
    def system_overview():
        try:
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_active = true")
                total_staff = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
                total_beds = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
                occupied_beds = cursor.fetchone()['count']
                
                return jsonify({
                    "success": True,
                    "overview": {
                        "total_staff": total_staff,
                        "total_beds": total_beds,
                        "occupied_beds": occupied_beds,
                        "occupancy_rate": round((occupied_beds / total_beds) * 100, 1) if total_beds > 0 else 0
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