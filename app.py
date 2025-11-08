"""
app.py - PneumoTrack Enterprise Hospital Management System
PostgreSQL-Optimized Flask Application for Railway Deployment

DESCRIPTION:
Main application file that provides RESTful API endpoints for hospital management.
Features automatic PostgreSQL database initialization, bed management, staff scheduling,
and real-time monitoring capabilities.

ARCHITECTURE:
- PostgreSQL database with persistent storage on Railway
- Modular schema and seeder for clean separation of concerns
- Automatic database initialization on first deploy
- Comprehensive error handling and logging
- Production-ready security headers and CORS

AUTHOR: Hospital IT Team
VERSION: 4.0.0
LAST UPDATED: 2025
"""

import os
import logging
from urllib.parse import urlparse
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, current_app, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman
import psycopg
from psycopg.rows import dict_row

# =============================================================================
# CONFIGURATION CLASS FOR RAILWAY DEPLOYMENT
# =============================================================================
class RailwayConfig:
    """
    Configuration class optimized for Railway deployment environment.
    All sensitive values are loaded from environment variables with secure defaults.
    """
    
    # Server Configuration
    PORT = int(os.environ.get('PORT', 5000))  # Railway provides PORT environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Security & Rate Limiting
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', '2000'))
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))
    
    # Application Limits
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload


# =============================================================================
# DATABASE MANAGEMENT - POSTGRESQL OPTIMIZED
# =============================================================================
class DatabaseManager:
    """
    Advanced database management for PostgreSQL with connection pooling,
    error handling, and performance optimizations for production use.
    """
    
    def __init__(self, app):
        """
        Initialize database manager with Flask app context.
        
        Args:
            app: Flask application instance
        """
        self.app = app
    
    def get_connection(self):
        """
        Establish and return PostgreSQL database connection.
        Uses Railway's DATABASE_URL environment variable.
        
        Returns:
            psycopg.Connection: PostgreSQL connection object
            
        Raises:
            Exception: If DATABASE_URL is not configured or connection fails
        """
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            raise Exception("DATABASE_URL environment variable not configured. Please add PostgreSQL database to Railway.")
        
        try:
            # Use psycopg3 connection
            conn = psycopg.connect(
                database_url,
                row_factory=dict_row  # Return dictionaries for easier JSON serialization
            )
            return conn
        except Exception as e:
            current_app.logger.error(f"PostgreSQL connection failed: {e}")
            raise
    
    def get_cursor(self):
        """
        Context manager for database operations with automatic transaction handling.
        
        Yields:
            psycopg.Cursor: Database cursor that returns rows as dictionaries
        """
        conn = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            yield cursor
            conn.commit()  # Auto-commit if no exceptions
        except Exception as e:
            if conn:
                conn.rollback()  # Auto-rollback on error
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
    """
    AUTOMATIC DATABASE SETUP FOR RAILWAY POSTGRESQL DEPLOYMENT
    ==========================================================
    
    This function automatically handles database initialization scenarios
    that occur during Railway deployments with PostgreSQL:
    
    SCENARIOS HANDLED:
    1. First Deploy - No tables exist, runs schema + seeder
    2. Database Exists - Tables exist but empty, runs seeder only  
    3. Database Populated - Tables + data exist, does nothing
    
    LOGIC:
    - Checks if required tables exist using PostgreSQL information_schema
    - If no tables: Runs schema.py AND seeder.py (full setup)
    - If tables but no data: Runs seeder.py only (data population)
    - If tables + data exist: Does nothing (app ready)
    
    This ensures the app is always ready after Railway deployments
    while preserving existing data in PostgreSQL.
    """
    app.logger.info("🔧 Starting automatic database initialization check...")
    
    try:
        db_manager = DatabaseManager(app)
        
        # Check if database tables exist
        tables_exist = check_tables_exist(db_manager)
        
        if not tables_exist:
            # SCENARIO 1: First deployment - no tables exist
            app.logger.info("🚀 First deployment detected - creating database schema...")
            
            # Import and run schema creation
            try:
                from schema import create_tables
                create_tables()
                app.logger.info("✅ Database schema created successfully")
            except Exception as e:
                app.logger.error(f"❌ Schema creation failed: {e}")
                raise
            
            # Import and run data seeding
            try:
                from seeder import seed_data
                seed_data()
                app.logger.info("✅ Sample data seeded successfully")
            except Exception as e:
                app.logger.error(f"❌ Data seeding failed: {e}")
                # Don't raise error - app can run with empty tables
                
        else:
            # Tables exist, check if data is populated
            if is_database_empty(db_manager):
                # SCENARIO 2: Tables exist but no data
                app.logger.info("📊 Database tables exist but no data - seeding...")
                try:
                    from seeder import seed_data
                    seed_data()
                    app.logger.info("✅ Sample data seeded successfully")
                except Exception as e:
                    app.logger.error(f"❌ Data seeding failed: {e}")
            else:
                # SCENARIO 3: Database fully populated
                app.logger.info("✅ Database already populated and ready")
                
    except Exception as e:
        app.logger.error(f"⚠️ Auto-initialization warning: {e}")
        # Don't crash the app - continue without initialized database


def check_tables_exist(db_manager):
    """
    Check if all required database tables exist in PostgreSQL.
    
    Args:
        db_manager: DatabaseManager instance
        
    Returns:
        bool: True if all required tables exist, False otherwise
    """
    try:
        with db_manager.get_cursor() as cursor:
            # List of required tables for the application
            required_tables = [
                'hospital_system', 'department_units', 'medical_staff',
                'coverage_rules', 'guardia_schedules', 'enhanced_beds',
                'bed_audit_trail', 'patient_flow', 'medical_equipment',
                'daily_clinical_load', 'predictive_alerts', 'department_announcements'
            ]
            
            # Query PostgreSQL information_schema for existing tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
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
    """
    Check if database has any data in key tables.
    
    Args:
        db_manager: DatabaseManager instance
        
    Returns:
        bool: True if database is empty, False otherwise
    """
    try:
        with db_manager.get_cursor() as cursor:
            # Check medical staff table as indicator of data presence
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
            staff_count = cursor.fetchone()['count']
            
            # Check enhanced beds table
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            beds_count = cursor.fetchone()['count']
            
            is_empty = staff_count == 0 and beds_count == 0
            current_app.logger.info(f"📊 Database emptiness check - Staff: {staff_count}, Beds: {beds_count}")
            
            return is_empty
            
    except Exception as e:
        current_app.logger.error(f"❌ Error checking database emptiness: {e}")
        return True  # Assume empty if we can't check


# =============================================================================
# API ROUTE HANDLERS - HOSPITAL MANAGEMENT SYSTEM
# =============================================================================
def get_medical_staff():
    """
    Retrieve all active medical staff with their department information.
    
    Returns:
        JSON response with staff list or error message
    """
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
    """
    Retrieve guardia schedules with filtering options.
    
    Query Parameters:
        - date: Specific date to filter schedules (YYYY-MM-DD)
        - unit_id: Filter by department unit ID
        - staff_id: Filter by staff member ID
        
    Returns:
        JSON response with schedules or error message
    """
    try:
        # Get query parameters with defaults
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
            
            # Apply filters
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
    """
    Retrieve enhanced bed management data with patient information.
    
    Returns:
        JSON response with bed status, occupancy, and statistics
    """
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
            
            # Calculate bed statistics
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
    """
    Retrieve all active department units with capacity information.
    
    Returns:
        JSON response with department units or error message
    """
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
    """
    Retrieve current patient flow with bed assignments and doctor information.
    
    Returns:
        JSON response with patient information
    """
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
    """
    Get comprehensive system overview with key performance metrics.
    
    Returns:
        JSON response with system statistics and health status
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            # Get key performance metrics
            metrics = {}
            
            # Staff metrics
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_active = true")
            metrics['total_staff'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_on_call = true")
            metrics['on_call_staff'] = cursor.fetchone()['count']
            
            # Bed metrics
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
            metrics['total_beds'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds WHERE status = 'occupied'")
            metrics['occupied_beds'] = cursor.fetchone()['count']
            
            # Patient metrics
            cursor.execute("SELECT COUNT(*) as count FROM patient_flow WHERE current_status = 'admitted'")
            metrics['active_patients'] = cursor.fetchone()['count']
            
            cursor.execute("SELECT COUNT(*) as count FROM patient_flow WHERE acuity_level = 'critical'")
            metrics['critical_patients'] = cursor.fetchone()['count']
            
            # Today's schedules
            cursor.execute("SELECT COUNT(*) as count FROM guardia_schedules WHERE schedule_date = CURRENT_DATE")
            metrics['today_schedules'] = cursor.fetchone()['count']
            
            # Calculate occupancy rate
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


# =============================================================================
# COMPATIBILITY API ENDPOINTS - FRONTEND SUPPORT
# =============================================================================

def get_system_status():
    """
    System status endpoint for frontend health checks.
    
    Returns:
        JSON response with system status information
    """
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
    """
    Retrieve medical equipment inventory.
    
    Returns:
        JSON response with equipment list
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM medical_equipment 
                ORDER BY equipment_type, status
            """)
            equipment = cursor.fetchall()
            return jsonify({"success": True, "equipment": equipment})
    except Exception as e:
        current_app.logger.error(f"Equipment retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve equipment"}), 500


def get_intelligent_alerts():
    """
    Retrieve active intelligent alerts.
    
    Returns:
        JSON response with alerts list
    """
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


def get_clinical_load():
    """
    Retrieve recent clinical load data.
    
    Returns:
        JSON response with clinical load information
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM daily_clinical_load 
                ORDER BY report_date DESC 
                LIMIT 7
            """)
            clinical_load = cursor.fetchall()
            return jsonify({"success": True, "clinical_load": clinical_load})
    except Exception as e:
        current_app.logger.error(f"Clinical load retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve clinical load"}), 500


def get_announcements():
    """
    Retrieve active department announcements.
    
    Returns:
        JSON response with announcements list
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT * FROM department_announcements 
                WHERE effective_from <= CURRENT_DATE 
                AND (effective_until IS NULL OR effective_until >= CURRENT_DATE)
                ORDER BY priority_level DESC, created_at DESC
            """)
            announcements = cursor.fetchall()
            return jsonify({"success": True, "announcements": announcements})
    except Exception as e:
        current_app.logger.error(f"Announcements retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve announcements"}), 500


def get_absence_requests():
    """
    Retrieve pending absence requests.
    
    Returns:
        JSON response with absence requests
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT ar.*, 
                       ms.first_name || ' ' || ms.last_name as staff_name,
                       ms.role as staff_role
                FROM absence_requests ar
                JOIN medical_staff ms ON ar.staff_id = ms.id
                WHERE ar.status = 'pending'
                ORDER BY ar.start_date
            """)
            absences = cursor.fetchall()
            return jsonify({"success": True, "absences": absences})
    except Exception as e:
        current_app.logger.error(f"Absence requests retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve absence requests"}), 500


def get_analytics_dashboard():
    """
    Retrieve analytics dashboard data.
    
    Returns:
        JSON response with analytics metrics
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            # Get basic analytics
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


def get_staff_availability():
    """
    Retrieve staff availability data.
    
    Returns:
        JSON response with staff availability information
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    ms.id,
                    ms.first_name || ' ' || ms.last_name as staff_name,
                    ms.role,
                    ms.current_status,
                    ms.is_on_call,
                    du.name as unit_name,
                    COUNT(gs.id) as scheduled_shifts
                FROM medical_staff ms
                LEFT JOIN department_units du ON ms.primary_unit_id = du.id
                LEFT JOIN guardia_schedules gs ON ms.id = gs.staff_id AND gs.schedule_date = CURRENT_DATE
                WHERE ms.is_active = true
                GROUP BY ms.id, du.name
                ORDER BY ms.role, ms.last_name
            """)
            availability = cursor.fetchall()
            return jsonify({"success": True, "availability": availability})
    except Exception as e:
        current_app.logger.error(f"Staff availability error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve staff availability"}), 500


# =============================================================================
# APPLICATION FACTORY AND ROUTE REGISTRATION
# =============================================================================

def create_app(config_class=RailwayConfig):
    """
    Flask application factory pattern for creating app instances.
    
    Args:
        config_class: Configuration class to use
        
    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # =========================================================================
    # SECURITY MIDDLEWARE SETUP
    # =========================================================================
    
    # CORS - Configure for frontend access
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)
    
    # Talisman for security headers
    Talisman(
        app,
        content_security_policy=None,
        force_https=os.environ.get('RAILWAY_ENVIRONMENT') == 'production',
        strict_transport_security=True
    )
    
    # Rate limiting to prevent abuse
    limiter = Limiter(
        app=app,
        key_func=get_remote_address,
        default_limits=[f"{config_class.RATE_LIMIT_PER_HOUR}/hour"],
        storage_uri="memory://",
        strategy="fixed-window"
    )
    
    # =========================================================================
    # LOGGING CONFIGURATION
    # =========================================================================
    logging.basicConfig(
        level=logging.INFO if os.environ.get('RAILWAY_ENVIRONMENT') == 'production' else logging.DEBUG,
        format='%(asctime)s %(levelname)s: %(message)s [%(name)s:%(lineno)d]'
    )
    app.logger.setLevel(logging.INFO)
    
    # =========================================================================
    # DATABASE INITIALIZATION WITH AUTO-SETUP
    # =========================================================================
    with app.app_context():
        # Run auto-initialization for Railway deployments
        app.logger.info("🚀 Starting application with PostgreSQL database...")
        auto_initialize_database(app)
    
    # =========================================================================
    # ROUTE REGISTRATION - HOSPITAL MANAGEMENT API
    # =========================================================================
    
    # Serve frontend static files
    @app.route('/')
    def serve_index():
        """Serve the main frontend application."""
        return render_template('index.html')

    @app.route('/beds')
    def serve_beds():
        """Serve the bed management interface."""
        return render_template('beds.html')

    # Static file serving
    @app.route('/static/<path:path>')
    def serve_static(path):
        """Serve static files from static directory."""
        return send_from_directory('static', path)
    
    @app.route('/<path:path>')
    def serve_all_static(path):
        """Serve other static files."""
        return send_from_directory('.', path)
    
    # Health check endpoint for monitoring
    @app.route('/api/health')
    def health_check():
        """Health check endpoint for deployment monitoring."""
        return jsonify({
            "status": "healthy",
            "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'development'),
            "timestamp": datetime.now().isoformat(),
            "version": "4.0.0"
        })
    
    # =========================================================================
    # HOSPITAL MANAGEMENT API ENDPOINTS
    # =========================================================================
    
    # Medical Staff Management
    @app.route('/api/medical-staff')
    def medical_staff():
        """Get all active medical staff."""
        return get_medical_staff()
    
    @app.route('/api/staff')
    def staff_compat():
        """Compatibility endpoint for staff data."""
        return get_medical_staff()
    
    # Guardia Schedules
    @app.route('/api/guardia-schedules')
    def guardia_schedules():
        """Get guardia schedules with optional filtering."""
        return get_guardia_schedules()
    
    @app.route('/api/guardia/schedule')
    def guardia_schedule_compat():
        """Compatibility endpoint for guardia schedules."""
        return get_guardia_schedules()
    
    # Bed Management
    @app.route('/api/enhanced-beds')
    def enhanced_beds():
        """Get enhanced bed management data."""
        return get_enhanced_beds()
    
    @app.route('/api/beds')
    def beds_compat():
        """Compatibility endpoint for bed data."""
        return get_enhanced_beds()
    
    @app.route('/api/beds/enhanced')
    def enhanced_beds_compat():
        """Specific endpoint for enhanced beds."""
        return get_enhanced_beds()
    
    # Department Units
    @app.route('/api/department-units')
    def department_units():
        """Get all active department units."""
        return get_department_units()
    
    @app.route('/api/units')
    def units_compat():
        """Compatibility endpoint for department units."""
        return get_department_units()
    
    # Patient Flow
    @app.route('/api/patient-flow')
    def patient_flow():
        """Get current patient flow information."""
        return get_patient_flow()
    
    # System Overview
    @app.route('/api/system-overview')
    def system_overview():
        """Get comprehensive system overview and metrics."""
        return get_system_overview()
    
    @app.route('/api/dashboard/summary')
    def dashboard_summary_compat():
        """Compatibility endpoint for dashboard summary."""
        return get_system_overview()
    
    # =========================================================================
    # COMPATIBILITY API ENDPOINTS
    # =========================================================================
    
    @app.route('/api/system/status')
    def system_status():
        """System status endpoint for frontend compatibility."""
        return get_system_status()
    
    @app.route('/api/equipment')
    def equipment():
        """Get medical equipment data."""
        return get_equipment()
    
    @app.route('/api/alerts/intelligent')
    def intelligent_alerts():
        """Get intelligent alerts data."""
        return get_intelligent_alerts()
    
    @app.route('/api/clinical/load')
    def clinical_load():
        """Get clinical load data."""
        return get_clinical_load()
    
    @app.route('/api/announcements')
    def announcements():
        """Get department announcements."""
        return get_announcements()
    
    @app.route('/api/absence/requests')
    def absence_requests():
        """Get absence requests."""
        return get_absence_requests()
    
    @app.route('/api/analytics/dashboard')
    def analytics_dashboard():
        """Get analytics dashboard data."""
        return get_analytics_dashboard()
    
    @app.route('/api/staff/availability')
    def staff_availability():
        """Get staff availability data."""
        return get_staff_availability()
    
    # =========================================================================
    # ADMINISTRATION AND DEBUG ENDPOINTS
    # =========================================================================
    
    @app.route('/api/admin/initialize-database', methods=['POST'])
    def manual_initialize_database():
        """
        Manual endpoint to force database initialization.
        Useful for development and testing.
        
        Returns:
            JSON response with initialization status
        """
        try:
            app.logger.info("🛠️ Manual database initialization triggered via API")
            
            # Force run the auto-initialization
            auto_initialize_database(app)
            
            return jsonify({
                "success": True,
                "message": "Database initialization completed",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/debug/database')
    def debug_database():
        """
        Debug endpoint to check database status and configuration.
        
        Returns:
            JSON response with database status information
        """
        try:
            db_manager = DatabaseManager(app)
            with db_manager.get_cursor() as cursor:
                # Check if tables exist
                cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                tables = [row['table_name'] for row in cursor.fetchall()]
                
                # Check data counts in key tables
                cursor.execute("SELECT COUNT(*) as count FROM medical_staff")
                staff_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
                beds_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM department_units")
                units_count = cursor.fetchone()['count']
                
            return jsonify({
                "success": True,
                "database_status": {
                    "tables_exist": len(tables) > 0,
                    "tables_found": tables,
                    "staff_count": staff_count,
                    "beds_count": beds_count,
                    "units_count": units_count,
                    "database_url_configured": bool(os.environ.get('DATABASE_URL')),
                    "environment": os.environ.get('RAILWAY_ENVIRONMENT', 'development')
                }
            })
        except Exception as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "database_status": "error"
            }), 500
    
    @app.route('/api/health/check')
    def health_check_detailed():
        """
        Detailed health check including database connectivity and data status.
        
        Returns:
            JSON response with comprehensive health information
        """
        try:
            db_manager = DatabaseManager(app)
            with db_manager.get_cursor() as cursor:
                # Check key tables
                cursor.execute("SELECT COUNT(*) as count FROM medical_staff WHERE is_active = true")
                active_staff = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM enhanced_beds")
                total_beds = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM department_units WHERE is_active = true")
                active_units = cursor.fetchone()['count']
                
                health_status = {
                    "api": "healthy",
                    "database": "healthy" if active_staff > 0 and total_beds > 0 else "degraded",
                    "data_loaded": active_staff > 0 and total_beds > 0,
                    "stats": {
                        "active_staff": active_staff,
                        "total_beds": total_beds,
                        "active_units": active_units
                    }
                }
                
                return jsonify({
                    "success": True,
                    "status": "healthy" if health_status["data_loaded"] else "degraded",
                    "health": health_status,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            return jsonify({
                "success": False,
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }), 500
    
    # =========================================================================
    # ERROR HANDLERS
    # =========================================================================
    @app.errorhandler(404)
    def not_found(e):
        """Handle 404 - Not Found errors."""
        return jsonify({"success": False, "error": "Endpoint not found"}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(e):
        """Handle 405 - Method Not Allowed errors."""
        return jsonify({"success": False, "error": "Method not allowed"}), 405
    
    @app.errorhandler(500)
    def server_error(e):
        """Handle 500 - Internal Server errors."""
        app.logger.error(f"500 error: {str(e)}")
        return jsonify({"success": False, "error": "Internal server error"}), 500
    
    @app.errorhandler(413)
    def too_large(e):
        """Handle 413 - Request Too Large errors."""
        return jsonify({"success": False, "error": "Request body too large"}), 413
    
    # =========================================================================
    # REQUEST MIDDLEWARE
    # =========================================================================
    @app.before_request
    def log_request_info():
        """Log basic request information for all endpoints except static files."""
        if request.endpoint and request.endpoint != 'static':
            app.logger.info(f"{request.method} {request.path} - IP: {request.remote_addr}")
    
    @app.after_request
    def add_security_headers(response):
        """Add security headers to all responses."""
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # HSTS for production
        if os.environ.get('RAILWAY_ENVIRONMENT') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    return app


# =============================================================================
# APPLICATION STARTUP
# =============================================================================

# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    """
    Main application entry point when run directly.
    Configured for Railway deployment with proper host and port binding.
    """
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('RAILWAY_ENVIRONMENT') != 'production'
    
    app.logger.info(f"🚀 Starting PneumoTrack Enterprise on port {port}")
    app.logger.info(f"🔧 Debug mode: {debug}")
    app.logger.info(f"🏥 Environment: {os.environ.get('RAILWAY_ENVIRONMENT', 'development')}")
    app.logger.info(f"🗄️ Database: PostgreSQL (Railway)")
    
    # Start Flask development server
    app.run(
        host='0.0.0.0',  # Bind to all interfaces for Railway
        port=port,
        debug=debug,
        threaded=True  # Handle multiple requests concurrently
    )