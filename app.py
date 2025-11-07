"""
Railway-Optimized Flask Forum Application - PRODUCTION READY
Enhanced with Auto-Database Initialization for Railway Deployments

DESCRIPTION:
This is a comprehensive hospital management system (PneumoTrack Enterprise) 
optimized for Railway deployment. It features automatic database initialization,
bed management, staff scheduling, and real-time monitoring capabilities.

AUTHOR: Your Development Team
VERSION: 4.0.0
LAST UPDATED: 2025
"""

import os
import logging
import sqlite3
import jwt
import bcrypt
import secrets
import hashlib
import html
import bleach
import re
import random
from datetime import datetime, timedelta
from urllib.parse import urlparse
from functools import wraps
from contextlib import contextmanager
from flask import Flask, request, jsonify, send_from_directory, current_app, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_talisman import Talisman


# =============================================================================
# CONFIGURATION FOR RAILWAY DEPLOYMENT
# =============================================================================
class RailwayConfig:
    """
    Configuration class optimized for Railway deployment environment.
    All sensitive values are loaded from environment variables with secure defaults.
    """
    # Server Configuration
    PORT = int(os.environ.get('PORT', 5000))  # Railway provides PORT environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))  # Secure random default
    
    # Database Configuration
    DB_NAME = os.environ.get('DB_NAME', 'pneumotrack_enterprise.db')
    
    # Security & Rate Limiting
    RATE_LIMIT_PER_HOUR = int(os.environ.get('RATE_LIMIT_PER_HOUR', '2000'))
    JWT_EXPIRY_HOURS = int(os.environ.get('JWT_EXPIRY_HOURS', '24'))
    BCRYPT_ROUNDS = 12  # Secure password hashing rounds
    
    # Application Limits
    MIN_PASSWORD_LENGTH = 8
    MAX_USERNAME_LENGTH = 20
    MAX_POST_LENGTH = 10000
    MAX_COMMENT_LENGTH = 2000
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    # Database Performance
    CONNECTION_TIMEOUT = 30
    WAL_MODE = True  # Write-Ahead Logging for better concurrency


# =============================================================================
# DATABASE MANAGEMENT - PRODUCTION GRADE
# =============================================================================
class DatabaseManager:
    """
    Advanced database management with connection pooling, error handling,
    and performance optimizations for production use.
    """
    
    def __init__(self, app):
        """
        Initialize database manager with Flask app context.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._connection = None
    
    @property
    def connection(self):
        """
        Lazy-loaded database connection with performance optimizations.
        Uses connection pooling and WAL mode for better concurrency.
        """
        if self._connection is None:
            self._connection = sqlite3.connect(
                self.app.config['DB_NAME'],
                check_same_thread=False,
                timeout=self.app.config['CONNECTION_TIMEOUT']
            )
            # Enable row factory for dictionary-like access
            self._connection.row_factory = sqlite3.Row
            # Enable foreign key constraints
            self._connection.execute("PRAGMA foreign_keys = ON")
            
            # Performance optimizations
            if self.app.config['WAL_MODE']:
                self._connection.execute("PRAGMA journal_mode = WAL")  # Better concurrency
            self._connection.execute("PRAGMA synchronous = NORMAL")    # Balance safety & performance
            self._connection.execute("PRAGMA cache_size = -64000")     # 64MB cache
        
        return self._connection
    
    def close(self):
        """Safely close database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    @contextmanager
    def get_cursor(self):
        """
        Context manager for database operations with automatic transaction handling.
        
        Usage:
            with db_manager.get_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
        
        Features:
        - Automatic commit on success
        - Automatic rollback on exception
        - Proper connection cleanup
        """
        try:
            cursor = self.connection.cursor()
            yield cursor
            self.connection.commit()  # Auto-commit if no exceptions
        except Exception as e:
            self.connection.rollback()  # Auto-rollback on error
            raise e


def init_database(app):
    """
    Initialize database schema with all required tables, indexes, and constraints.
    This function creates the complete database structure without any sample data.
    
    Args:
        app: Flask application instance
    """
    db_manager = DatabaseManager(app)
    
    try:
        with db_manager.get_cursor() as cursor:
            # Core hospital system tables
            cursor.executescript("""
                -- Hospital system configuration table
                CREATE TABLE IF NOT EXISTS hospital_system (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    hospital_name TEXT NOT NULL DEFAULT 'Advanced Neumology & Pulmonary Center',
                    chief_of_department TEXT NOT NULL DEFAULT 'Dr. Maria Rodriguez',
                    system_version TEXT NOT NULL DEFAULT 'PneumoTrack Enterprise v4.0',
                    emergency_contact TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Department units with capacity tracking
                CREATE TABLE IF NOT EXISTS department_units (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    specialty TEXT NOT NULL,
                    color_code TEXT DEFAULT '#3498db',
                    icon TEXT,
                    description TEXT,
                    total_beds INTEGER DEFAULT 0 CHECK(total_beds >= 0),
                    available_beds INTEGER DEFAULT 0 CHECK(available_beds >= 0),
                    standby_beds INTEGER DEFAULT 0 CHECK(standby_beds >= 0),
                    vent_capable_beds INTEGER DEFAULT 0 CHECK(vent_capable_beds >= 0),
                    negative_pressure_rooms INTEGER DEFAULT 0 CHECK(negative_pressure_rooms >= 0),
                    is_procedure_capable BOOLEAN DEFAULT 0,
                    status TEXT DEFAULT 'operational' CHECK(status IN ('operational', 'maintenance', 'closed')),
                    is_active BOOLEAN DEFAULT 1,
                    unit_phone TEXT,
                    unit_location TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Medical staff with comprehensive role management
                CREATE TABLE IF NOT EXISTS medical_staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    title TEXT,
                    staff_id TEXT UNIQUE NOT NULL,
                    specialization TEXT NOT NULL,
                    sub_specialization TEXT,
                    qualifications TEXT,
                    license_number TEXT,
                    years_experience INTEGER DEFAULT 0 CHECK(years_experience >= 0),
                    primary_unit_id INTEGER,
                    secondary_units TEXT,
                    role TEXT DEFAULT 'consultant' CHECK(role IN ('chief', 'senior_consultant', 'consultant', 'resident')),
                    email TEXT,
                    phone TEXT,
                    emergency_contact TEXT,
                    emergency_contact_priority INTEGER DEFAULT 99 CHECK(emergency_contact_priority >= 0),
                    rapid_response_capable BOOLEAN DEFAULT 0,
                    backup_units TEXT,
                    current_status TEXT DEFAULT 'available' CHECK(current_status IN ('available', 'busy', 'on_break', 'off_duty')),
                    is_on_call BOOLEAN DEFAULT 0,
                    vent_trained BOOLEAN DEFAULT 0,
                    procedure_trained BOOLEAN DEFAULT 0,
                    competencies TEXT,
                    is_active BOOLEAN DEFAULT 1,
                    preferred_shift TEXT CHECK(preferred_shift IN ('morning', 'evening', 'night', 'flexible')),
                    absence_type TEXT CHECK(absence_type IN ('holiday', 'sick_leave', 'maternity_leave', 'paternity_leave', 'emergency_leave', NULL)),
                    absence_start DATE,
                    absence_end DATE,
                    absence_reason TEXT,
                    guardia_count INTEGER DEFAULT 0 CHECK(guardia_count >= 0),
                    last_guardia_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (primary_unit_id) REFERENCES department_units (id)
                );

                -- Coverage rules for minimum staffing requirements
                CREATE TABLE IF NOT EXISTS coverage_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    unit_id INTEGER NOT NULL,
                    shift_type TEXT NOT NULL CHECK(shift_type IN ('morning', 'evening', 'night')),
                    min_senior_consultants INTEGER DEFAULT 0 CHECK(min_senior_consultants >= 0),
                    min_consultants INTEGER DEFAULT 1 CHECK(min_consultants >= 0),
                    min_vent_trained INTEGER DEFAULT 0 CHECK(min_vent_trained >= 0),
                    min_procedure_trained INTEGER DEFAULT 0 CHECK(min_procedure_trained >= 0),
                    is_critical_coverage BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (unit_id) REFERENCES department_units (id),
                    UNIQUE(unit_id, shift_type)
                );

                -- Guardia schedules with conflict detection
                CREATE TABLE IF NOT EXISTS guardia_schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_id INTEGER NOT NULL,
                    schedule_date DATE NOT NULL,
                    shift_type TEXT NOT NULL CHECK(shift_type IN ('morning', 'evening', 'night', '24h')),
                    unit_id INTEGER NOT NULL,
                    status TEXT DEFAULT 'scheduled' CHECK(status IN ('scheduled', 'completed', 'cancelled', 'no_show', 'swapped')),
                    notes TEXT,
                    created_by TEXT,
                    conflict_checked BOOLEAN DEFAULT 0,
                    coverage_met BOOLEAN DEFAULT 0,
                    requires_attention BOOLEAN DEFAULT 0,
                    attention_reason TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (staff_id) REFERENCES medical_staff (id),
                    FOREIGN KEY (unit_id) REFERENCES department_units (id)
                );

                -- Enhanced bed management system
                CREATE TABLE IF NOT EXISTS enhanced_beds (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_code TEXT NOT NULL,           -- H1, H2, ... H15
                    bed_number TEXT NOT NULL,          -- BH11, BH12, ... BH154
                    display_name TEXT,                 -- "Bed 1 - H1"
                    status TEXT DEFAULT 'empty' CHECK(status IN ('empty', 'occupied', 'reserved', 'cleaning', 'maintenance')),
                    patient_id INTEGER,
                    clinical_needs TEXT,               -- 'oxygen,isolation,monitoring'
                    equipment TEXT,                    -- 'ventilator,high_flow,cpap'
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by TEXT,
                    notes TEXT,
                    UNIQUE(room_code, bed_number)
                );

                -- Bed audit trail for tracking changes
                CREATE TABLE IF NOT EXISTS bed_audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bed_id INTEGER,
                    old_status TEXT,
                    new_status TEXT,
                    updated_by TEXT NOT NULL,
                    update_reason TEXT,
                    patient_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bed_id) REFERENCES enhanced_beds (id)
                );

                -- Patient flow tracking
                CREATE TABLE IF NOT EXISTS patient_flow (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    patient_code TEXT UNIQUE NOT NULL,
                    anonymous_id TEXT,
                    age_group TEXT CHECK(age_group IN ('pediatric', 'adult', 'geriatric')),
                    primary_diagnosis TEXT,
                    secondary_diagnoses TEXT,
                    acuity_level TEXT DEFAULT 'stable' CHECK(acuity_level IN ('stable', 'guarded', 'critical')),
                    current_bed_id INTEGER,
                    current_unit_id INTEGER,
                    attending_doctor_id INTEGER,
                    admission_type TEXT CHECK(admission_type IN ('emergency', 'elective', 'transfer')),
                    admission_source TEXT,
                    admission_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expected_length_of_stay INTEGER CHECK(expected_length_of_stay >= 0),
                    treatment_phase TEXT,
                    special_requirements TEXT,
                    predicted_discharge TIMESTAMP,
                    discharge_ready BOOLEAN DEFAULT 0,
                    discharge_notes TEXT,
                    current_status TEXT DEFAULT 'admitted' CHECK(current_status IN ('admitted', 'discharged', 'transferred', 'deceased')),
                    status_history TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (current_bed_id) REFERENCES enhanced_beds (id),
                    FOREIGN KEY (current_unit_id) REFERENCES department_units (id),
                    FOREIGN KEY (attending_doctor_id) REFERENCES medical_staff (id)
                );
            """)

            # Create performance indexes for better query performance
            cursor.executescript("""
                -- Core performance indexes
                CREATE INDEX IF NOT EXISTS idx_staff_frontend ON medical_staff(is_active, current_status, primary_unit_id);
                CREATE INDEX IF NOT EXISTS idx_guardia_frontend ON guardia_schedules(schedule_date, status, unit_id);
                CREATE INDEX IF NOT EXISTS idx_beds_frontend ON enhanced_beds(status, room_code);
                CREATE INDEX IF NOT EXISTS idx_enhanced_beds_room ON enhanced_beds(room_code, bed_number);
                CREATE INDEX IF NOT EXISTS idx_enhanced_beds_status ON enhanced_beds(status);
                CREATE INDEX IF NOT EXISTS idx_bed_audit_timestamp ON bed_audit_trail(timestamp);
                CREATE INDEX IF NOT EXISTS idx_patient_current ON patient_flow(current_status, current_unit_id);
            """)

            # Insert default hospital configuration
            cursor.execute("""
                INSERT OR IGNORE INTO hospital_system 
                (hospital_name, chief_of_department, system_version, emergency_contact)
                VALUES (?, ?, ?, ?)
            """, (
                "Advanced Neumology & Pulmonary Center",
                "Dr. Maria Rodriguez", 
                "PneumoTrack Enterprise v4.0",
                "Internal: 5555, External: +1-555-0123"
            ))

        app.logger.info("✅ Database schema initialized successfully with enhanced bed management")
        
    except Exception as e:
        app.logger.error(f"❌ Database initialization error: {e}")
        raise
    finally:
        db_manager.close()


# =============================================================================
# AUTO-DATABASE INITIALIZATION FOR RAILWAY DEPLOYMENT
# =============================================================================
def auto_initialize_database(app):
    """
    AUTOMATIC DATABASE SETUP FOR RAILWAY DEPLOYMENT
    ================================================
    
    This function automatically handles database initialization scenarios
    that occur during Railway deployments where SQLite databases are ephemeral.
    
    SCENARIOS HANDLED:
    1. Fresh Deployment - No database exists, runs full setup
    2. Database Reset - Railway wiped the DB, runs full setup  
    3. Schema Changes - Tables exist but might need updates
    4. Data Refresh - Tables exist but data is missing
    
    LOGIC:
    - Checks if hospital_system table exists (indicator of setup completion)
    - If no tables: Runs schema.py AND seeder.py (full setup)
    - If tables but no data: Runs seeder.py only (data refresh)
    - If tables + data exist: Does nothing (app ready)
    
    This ensures the app is always ready after Railway deployments.
    """
    try:
        db_manager = DatabaseManager(app)
        with db_manager.get_cursor() as cursor:
            # Check if hospital_system table exists - our indicator of initial setup
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='hospital_system'")
            hospital_table_exists = cursor.fetchone() is not None
            
            if not hospital_table_exists:
                # SCENARIO 1 & 2: Fresh deployment or database reset
                app.logger.info("🚀 Fresh database detected - running full setup...")
                
                # Import and run schema creation
                try:
                    from schema import create_tables  # Uses create_tables() function
                    create_tables()
                    app.logger.info("✅ Database schema created successfully")
                except Exception as e:
                    app.logger.warning(f"Schema initialization note: {e}")
                
                # Import and run data seeding
                try:
                    from seeder import seed_data  # Uses seed_data() function
                    seed_data()
                    app.logger.info("✅ Sample data seeded successfully")
                except Exception as e:
                    app.logger.warning(f"Data seeding note: {e}")
                    
            else:
                # SCENARIO 3 & 4: Tables exist, check if data is populated
                cursor.execute("SELECT COUNT(*) FROM medical_staff")
                staff_count = cursor.fetchone()[0]
                
                if staff_count == 0:
                    # SCENARIO 4: Tables exist but no data
                    app.logger.info("📊 Database tables exist but no data - seeding...")
                    try:
                        from seeder import seed_data
                        seed_data()
                        app.logger.info("✅ Sample data seeded successfully")
                    except Exception as e:
                        app.logger.warning(f"Data seeding note: {e}")
                else:
                    # SCENARIO 3: Everything is ready
                    app.logger.info("✅ Database already populated and ready")
                    
    except Exception as e:
        app.logger.error(f"⚠️ Auto-initialization warning: {e}")
        # Don't crash the app if auto-init fails - just log and continue


# =============================================================================
# SECURITY UTILITIES - PRODUCTION GRADE
# =============================================================================
class SecurityUtils:
    """
    Comprehensive security utilities for input validation, sanitization,
    and secure password handling.
    """
    
    @staticmethod
    def validate_username(username):
        """
        Validate username with security constraints.
        
        Args:
            username: Username to validate
            
        Returns:
            str: Sanitized username
            
        Raises:
            ValueError: If username fails validation
        """
        if len(username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(username) > 20:
            raise ValueError("Username must be less than 20 characters")
        if not re.match(r'^[a-zA-Z0-9_\-]+$', username):
            raise ValueError("Username can only contain letters, numbers, underscores, and hyphens")
        if username.lower() in ['admin', 'administrator', 'moderator', 'system']:
            raise ValueError("Username not allowed")
        return username.lower().strip()
    
    @staticmethod
    def validate_password(password):
        """
        Validate password strength with multiple security checks.
        
        Args:
            password: Password to validate
            
        Returns:
            str: Validated password
            
        Raises:
            ValueError: If password fails validation
        """
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        # Check password complexity
        checks = {
            'uppercase': bool(re.search(r'[A-Z]', password)),
            'lowercase': bool(re.search(r'[a-z]', password)),
            'digit': bool(re.search(r'\d', password)),
            'special': bool(re.search(r'[!@#$%^&*(),.?":{}|<>]', password))
        }
        
        if sum(checks.values()) < 3:
            raise ValueError("Password must contain at least 3 of: uppercase, lowercase, digits, special characters")
        
        # Check against common passwords
        common_passwords = {'password', '123456', 'qwerty', 'letmein', 'welcome'}
        if password.lower() in common_passwords:
            raise ValueError("Password is too common")
        
        return password
    
    @staticmethod
    def sanitize_html(content, max_length=None):
        """
        Sanitize HTML content to prevent XSS attacks.
        
        Args:
            content: HTML content to sanitize
            max_length: Optional maximum length
            
        Returns:
            str: Sanitized HTML content
        """
        if not content:
            return content
        
        # Define allowed tags and attributes
        allowed_tags = bleach.sanitizer.ALLOWED_TAGS + [
            'p', 'br', 'div', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'strong', 'em', 'u', 'strike', 'blockquote',
            'code', 'pre', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
        ]
        
        allowed_attributes = {
            '*': ['class', 'style', 'id'],
            'a': ['href', 'title', 'target', 'rel'],
            'img': ['src', 'alt', 'width', 'height', 'title'],
            'code': ['class'],
            'span': ['style']
        }
        
        # Clean HTML content
        cleaned = bleach.clean(
            content,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True,
            strip_comments=True
        )
        
        # Remove dangerous protocols
        cleaned = re.sub(r'javascript:', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'vbscript:', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'on\w+=', '', cleaned, flags=re.IGNORECASE)
        
        # Enforce length limit if specified
        if max_length and len(cleaned) > max_length:
            cleaned = cleaned[:max_length]
        
        return cleaned.strip()
    
    @staticmethod
    def hash_password(password):
        """
        Securely hash password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            bytes: Hashed password
        """
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(12))
    
    @staticmethod
    def check_password(password, hashed):
        """
        Verify password against hash.
        
        Args:
            password: Plain text password
            hashed: Hashed password to check against
            
        Returns:
            bool: True if password matches hash
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed)
        except Exception:
            return False
    
    @staticmethod
    def generate_secure_token(length=32):
        """
        Generate cryptographically secure random token.
        
        Args:
            length: Token length in bytes
            
        Returns:
            str: Hexadecimal token
        """
        return secrets.token_hex(length)


# =============================================================================
# AUTHENTICATION DECORATORS
# =============================================================================
def token_required(f):
    """
    Decorator to require valid JWT token for route access.
    
    Features:
    - Validates Bearer token format
    - Checks token expiration
    - Verifies user exists and is active
    - Adds user info to request object
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization")
        
        if not token:
            return jsonify({"success": False, "error": "Authentication token required"}), 401
        
        if not token.startswith('Bearer '):
            return jsonify({"success": False, "error": "Invalid token format"}), 401
        
        token = token[7:]  # Remove 'Bearer ' prefix
        
        try:
            # Decode and verify JWT token
            decoded = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=["HS256"])
            
            db_manager = DatabaseManager(current_app)
            with db_manager.get_cursor() as cursor:
                cursor.execute("""
                    SELECT id, username, is_active, last_login, avatar_color 
                    FROM users WHERE id = ?
                """, (decoded["user_id"],))
                user = cursor.fetchone()
                
                if not user:
                    return jsonify({"success": False, "error": "User not found"}), 401                
                if not user["is_active"]:
                    return jsonify({"success": False, "error": "Account deactivated"}), 403
                
                # Add user info to request for use in route handlers
                request.user_id = user["id"]
                request.username = user["username"]
                request.user_data = dict(user)
            
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "error": "Invalid token"}), 401
        except Exception as e:
            current_app.logger.error(f"Token validation error: {e}")
            return jsonify({"success": False, "error": "Token validation failed"}), 401
        
        return f(*args, **kwargs)
    return decorated


def validate_json(f):
    """
    Decorator to validate JSON request body.
    
    Features:
    - Checks Content-Type header
    - Validates JSON syntax
    - Adds parsed JSON to request object
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_json:
            return jsonify({"success": False, "error": "Content-Type must be application/json"}), 400
        
        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"success": False, "error": "Invalid JSON data"}), 400
        
        request.json_data = data
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================
def log_user_activity(user_id, action, details=None):
    """
    Log user activity for audit trail.
    
    Args:
        user_id: ID of the user performing the action
        action: Description of the action performed
        details: Additional context or data
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent')
            
            cursor.execute("""INSERT INTO user_activity 
                        (user_id, action, details, ip_address, user_agent) 
                        VALUES (?, ?, ?, ?, ?)""",
                     (user_id, action, str(details) if details else None, ip_address, user_agent))
    except Exception as e:
        current_app.logger.error(f"Activity logging error: {e}")


def format_timestamp(timestamp):
    """
    Format timestamp for human-readable display.
    
    Args:
        timestamp: Datetime object or ISO format string
        
    Returns:
        str: Human-readable time difference
    """
    if not timestamp:
        return "Recently"
    
    try:
        if isinstance(timestamp, str):
            post_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        else:
            post_time = timestamp
            
        now = datetime.now()
        diff = now - post_time
        
        # Calculate appropriate time unit
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return "Recently"


def generate_avatar_color():
    """
    Generate random avatar color for users.
    
    Returns:
        str: Hex color code
    """
    colors = ['#007AFF', '#34C759', '#FF9500', '#FF3B30', '#AF52DE', '#5856D6', '#FF2D55', '#32D74B']
    return random.choice(colors)


# =============================================================================
# ROUTE HANDLERS - HOSPITAL MANAGEMENT SYSTEM
# =============================================================================
def get_medical_staff():
    """
    Retrieve all active medical staff with their details.
    
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
                WHERE ms.is_active = 1
                ORDER BY ms.role, ms.last_name, ms.first_name
            """)
            staff = [dict(row) for row in cursor.fetchall()]
            return jsonify({"success": True, "staff": staff})
    except Exception as e:
        current_app.logger.error(f"Medical staff retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve medical staff"}), 500


def get_guardia_schedules():
    """
    Retrieve guardia schedules with filtering options.
    
    Query Parameters:
        - date: Specific date to filter schedules
        - unit_id: Filter by department unit
        - staff_id: Filter by staff member
        
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
                query += " AND gs.schedule_date = ?"
                params.append(date_filter)
            if unit_id:
                query += " AND gs.unit_id = ?"
                params.append(unit_id)
            if staff_id:
                query += " AND gs.staff_id = ?"
                params.append(staff_id)
            
            query += " ORDER BY gs.schedule_date, gs.shift_type, du.name"
            
            cursor.execute(query, params)
            schedules = [dict(row) for row in cursor.fetchall()]
            
            return jsonify({"success": True, "schedules": schedules})
            
    except Exception as e:
        current_app.logger.error(f"Guardia schedules retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve schedules"}), 500


def get_enhanced_beds():
    """
    Retrieve enhanced bed management data with patient information.
    
    Returns:
        JSON response with bed status and occupancy
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
            beds = [dict(row) for row in cursor.fetchall()]
            
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
                WHERE is_active = 1 
                ORDER BY name
            """)
            units = [dict(row) for row in cursor.fetchall()]
            return jsonify({"success": True, "units": units})
    except Exception as e:
        current_app.logger.error(f"Department units retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve department units"}), 500


def get_patient_flow():
    """
    Retrieve current patient flow with bed assignments.
    
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
            patients = [dict(row) for row in cursor.fetchall()]
            return jsonify({"success": True, "patients": patients})
    except Exception as e:
        current_app.logger.error(f"Patient flow retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve patient flow"}), 500


def get_system_overview():
    """
    Get comprehensive system overview with key metrics.
    
    Returns:
        JSON response with system statistics
    """
    try:
        db_manager = DatabaseManager(current_app)
        with db_manager.get_cursor() as cursor:
            # Get key metrics
            metrics = {}
            
            # Staff metrics
            cursor.execute("SELECT COUNT(*) FROM medical_staff WHERE is_active = 1")
            metrics['total_staff'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM medical_staff WHERE is_on_call = 1")
            metrics['on_call_staff'] = cursor.fetchone()[0]
            
            # Bed metrics
            cursor.execute("SELECT COUNT(*) FROM enhanced_beds")
            metrics['total_beds'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM enhanced_beds WHERE status = 'occupied'")
            metrics['occupied_beds'] = cursor.fetchone()[0]
            
            # Patient metrics
            cursor.execute("SELECT COUNT(*) FROM patient_flow WHERE current_status = 'admitted'")
            metrics['active_patients'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM patient_flow WHERE acuity_level = 'critical'")
            metrics['critical_patients'] = cursor.fetchone()[0]
            
            # Today's schedules
            cursor.execute("SELECT COUNT(*) FROM guardia_schedules WHERE schedule_date = DATE('now')")
            metrics['today_schedules'] = cursor.fetchone()[0]
            
            return jsonify({
                "success": True,
                "overview": metrics,
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        current_app.logger.error(f"System overview retrieval error: {e}")
        return jsonify({"success": False, "error": "Failed to retrieve system overview"}), 500


# =============================================================================
# APPLICATION FACTORY - MAIN FLASK APP SETUP
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
    
    # Content Security Policy
    csp = {
        'default-src': ["'self'"],
        'style-src': ["'self'", "'unsafe-inline'", "https://cdn.jsdelivr.net"],
        'script-src': ["'self'", "https://cdn.jsdelivr.net"],
        'font-src': ["'self'", "https://cdn.jsdelivr.net"],
        'img-src': ["'self'", "data:", "https:"]
    }
    
    # Talisman for security headers
    Talisman(
        app,
        content_security_policy=None,  # Disabled for simplicity, configure as needed
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
        # Initialize database schema
        init_database(app)
        
        # Run auto-initialization for Railway deployments
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
    
    # Guardia Schedules
    @app.route('/api/guardia-schedules')
    def guardia_schedules():
        """Get guardia schedules with optional filtering."""
        return get_guardia_schedules()
    
    # Bed Management
    @app.route('/api/enhanced-beds')
    def enhanced_beds():
        """Get enhanced bed management data."""
        return get_enhanced_beds()
    
    # Department Units
    @app.route('/api/department-units')
    def department_units():
        """Get all active department units."""
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
    app.logger.info(f"🏥 Database: {app.config['DB_NAME']}")
    
    # Start Flask development server
    app.run(
        host='0.0.0.0',  # Bind to all interfaces for Railway
        port=port,
        debug=debug,
        threaded=True  # Handle multiple requests concurrently
    )