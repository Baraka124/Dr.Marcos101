"""
app.py - Complete Hospital Management System
Simple but full-featured version
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

# Configuration
class RailwayConfig:
    PORT = int(os.environ.get('PORT', 5000))
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    RATE_LIMIT_PER_HOUR = 2000

# Database Manager
class DatabaseManager:
    def __init__(self, app):
        self.app = app
    
    def get_connection(self):
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
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

# Auto-initialization
def auto_initialize_database(app):
    app.logger.info("🔧 Starting database initialization...")
    try:
        # Try to import and run schema/seeder
        try:
            from schema import create_tables
            create_tables()
            app.logger.info("✅ Schema created")
        except Exception as e:
            app.logger.error(f"❌ Schema failed: {e}")
        
        try:
            from seeder import seed_data
            seed_data()
            app.logger.info("✅ Data seeded")
        except Exception as e:
            app.logger.error(f"❌ Seeding failed: {e}")
            
    except Exception as e:
        app.logger.error(f"⚠️ Init warning: {e}")

# Create App
def create_app(config_class=RailwayConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    CORS(app)
    Talisman(app, content_security_policy=None)
    Limiter(app, key_func=get_remote_address, default_limits=["2000/hour"])
    
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    
    # Auto-init on startup
    with app.app_context():
        app.logger.info("🚀 Starting hospital management system...")
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
            "timestamp": datetime.now().isoformat(),
            "version": "4.0.0"
        })
    
    # API endpoints
    @app.route('/api/medical-staff')
    def medical_staff():
        try:
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT * FROM medical_staff WHERE is_active = true")
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
                cursor.execute("SELECT * FROM enhanced_beds")
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
                cursor.execute("SELECT * FROM department_units WHERE is_active = true")
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
                staff_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
                beds_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
                occupied_beds = cursor.fetchone()['count']
                
                return jsonify({
                    "success": True,
                    "overview": {
                        "total_staff": staff_count,
                        "total_beds": beds_count,
                        "occupied_beds": occupied_beds,
                        "occupancy_rate": round((occupied_beds / beds_count) * 100, 1) if beds_count > 0 else 0
                    }
                })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    # MANUAL INITIALIZATION ENDPOINT
    @app.route('/api/admin/initialize-database', methods=['POST'])
    def manual_initialize_database():
        try:
            app.logger.info("🛠️ Manual database initialization triggered")
            auto_initialize_database(app)
            return jsonify({
                "success": True,
                "message": "Database initialization completed"
            })
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    
    # DEBUG ENDPOINT
    @app.route('/api/debug/database')
    def debug_database():
        try:
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = [row['table_name'] for row in cursor.fetchall()]
                
                cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
                staff_count = cursor.fetchone()['count']
                
            return jsonify({
                "success": True,
                "tables_found": tables,
                "staff_count": staff_count,
                "database_connected": True
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "database_connected": False
            }), 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "error": "Internal server error"}), 500
    
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)