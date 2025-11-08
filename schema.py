"""
schema.py - PostgreSQL Table Creation Only
Creates empty table structure for Railway PostgreSQL deployment
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def get_database_connection():
    """
    Get database connection for Railway PostgreSQL
    Returns: PostgreSQL connection object
    """
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        logger.error("❌ DATABASE_URL environment variable not found")
        logger.info("💡 Please add PostgreSQL database to your Railway project")
        raise Exception("DATABASE_URL not configured")
    
    try:
        # Parse the database URL for PostgreSQL
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],  # Remove leading slash
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode='require'
        )
        logger.info("✅ Connected to Railway PostgreSQL")
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        raise

def create_tables():
    """
    Create all database tables with empty structure
    No sample data is inserted here
    """
    conn = None
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        logger.info("🗄️ Creating PostgreSQL tables...")
        
        # Hospital System Configuration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hospital_system (
                id SERIAL PRIMARY KEY,
                hospital_name TEXT NOT NULL DEFAULT 'Advanced Neumology & Pulmonary Center',
                chief_of_department TEXT NOT NULL DEFAULT 'Dr. Maria Rodriguez',
                system_version TEXT NOT NULL DEFAULT 'PneumoTrack Enterprise v4.0',
                emergency_contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Department Units
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS department_units (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                code TEXT UNIQUE NOT NULL,
                specialty TEXT NOT NULL,
                color_code TEXT DEFAULT '#3498db',
                icon TEXT,
                description TEXT,
                total_beds INTEGER DEFAULT 0 CHECK (total_beds >= 0),
                available_beds INTEGER DEFAULT 0 CHECK (available_beds >= 0),
                standby_beds INTEGER DEFAULT 0 CHECK (standby_beds >= 0),
                vent_capable_beds INTEGER DEFAULT 0 CHECK (vent_capable_beds >= 0),
                negative_pressure_rooms INTEGER DEFAULT 0 CHECK (negative_pressure_rooms >= 0),
                is_procedure_capable BOOLEAN DEFAULT FALSE,
                status TEXT DEFAULT 'operational' CHECK (status IN ('operational', 'maintenance', 'closed')),
                is_active BOOLEAN DEFAULT TRUE,
                unit_phone TEXT,
                unit_location TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Medical Staff - COMPLETE with all required columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medical_staff (
                id SERIAL PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                title TEXT,
                staff_id TEXT UNIQUE NOT NULL,
                specialization TEXT NOT NULL,
                sub_specialization TEXT,
                qualifications TEXT,
                license_number TEXT,
                years_experience INTEGER DEFAULT 0 CHECK (years_experience >= 0),
                primary_unit_id INTEGER REFERENCES department_units(id),
                secondary_units TEXT,
                role TEXT DEFAULT 'consultant' CHECK (role IN ('chief', 'senior_consultant', 'consultant', 'resident')),
                email TEXT,
                phone TEXT,
                emergency_contact TEXT,
                emergency_contact_priority INTEGER DEFAULT 99 CHECK (emergency_contact_priority >= 0),
                rapid_response_capable BOOLEAN DEFAULT FALSE,
                backup_units TEXT,
                current_status TEXT DEFAULT 'available' CHECK (current_status IN ('available', 'busy', 'on_break', 'off_duty')),
                is_on_call BOOLEAN DEFAULT FALSE,
                vent_trained BOOLEAN DEFAULT FALSE,
                procedure_trained BOOLEAN DEFAULT FALSE,
                competencies TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                preferred_shift TEXT CHECK (preferred_shift IN ('morning', 'evening', 'night', 'flexible')),
                absence_type TEXT CHECK (absence_type IN ('holiday', 'sick_leave', 'maternity_leave', 'paternity_leave', 'emergency_leave')),
                absence_start DATE,
                absence_end DATE,
                absence_reason TEXT,
                guardia_count INTEGER DEFAULT 0 CHECK (guardia_count >= 0),
                last_guardia_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Coverage Rules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS coverage_rules (
                id SERIAL PRIMARY KEY,
                unit_id INTEGER NOT NULL REFERENCES department_units(id),
                shift_type TEXT NOT NULL CHECK (shift_type IN ('morning', 'evening', 'night')),
                min_senior_consultants INTEGER DEFAULT 0 CHECK (min_senior_consultants >= 0),
                min_consultants INTEGER DEFAULT 1 CHECK (min_consultants >= 0),
                min_vent_trained INTEGER DEFAULT 0 CHECK (min_vent_trained >= 0),
                min_procedure_trained INTEGER DEFAULT 0 CHECK (min_procedure_trained >= 0),
                is_critical_coverage BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(unit_id, shift_type)
            )
        """)
        
        # Guardia Schedules
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guardia_schedules (
                id SERIAL PRIMARY KEY,
                staff_id INTEGER NOT NULL REFERENCES medical_staff(id),
                schedule_date DATE NOT NULL,
                shift_type TEXT NOT NULL CHECK (shift_type IN ('morning', 'evening', 'night', '24h')),
                unit_id INTEGER NOT NULL REFERENCES department_units(id),
                status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'no_show', 'swapped')),
                notes TEXT,
                created_by TEXT,
                conflict_checked BOOLEAN DEFAULT FALSE,
                coverage_met BOOLEAN DEFAULT FALSE,
                requires_attention BOOLEAN DEFAULT FALSE,
                attention_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Enhanced Bed Management System
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS enhanced_beds (
                id SERIAL PRIMARY KEY,
                room_code TEXT NOT NULL,
                bed_number TEXT NOT NULL,
                display_name TEXT,
                status TEXT DEFAULT 'empty' CHECK (status IN ('empty', 'occupied', 'reserved', 'cleaning', 'maintenance')),
                patient_id INTEGER,
                clinical_needs TEXT,
                equipment TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT,
                notes TEXT,
                UNIQUE(room_code, bed_number)
            )
        """)

        # Bed Audit Trail
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bed_audit_trail (
                id SERIAL PRIMARY KEY,
                bed_id INTEGER REFERENCES enhanced_beds(id),
                old_status TEXT,
                new_status TEXT,
                updated_by TEXT NOT NULL,
                update_reason TEXT,
                patient_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Patient Flow
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS patient_flow (
                id SERIAL PRIMARY KEY,
                patient_code TEXT UNIQUE NOT NULL,
                anonymous_id TEXT,
                age_group TEXT CHECK (age_group IN ('pediatric', 'adult', 'geriatric')),
                primary_diagnosis TEXT,
                secondary_diagnoses TEXT,
                acuity_level TEXT DEFAULT 'stable' CHECK (acuity_level IN ('stable', 'guarded', 'critical')),
                current_bed_id INTEGER REFERENCES enhanced_beds(id),
                current_unit_id INTEGER REFERENCES department_units(id),
                attending_doctor_id INTEGER REFERENCES medical_staff(id),
                admission_type TEXT CHECK (admission_type IN ('emergency', 'elective', 'transfer')),
                admission_source TEXT,
                admission_datetime TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expected_length_of_stay INTEGER CHECK (expected_length_of_stay >= 0),
                treatment_phase TEXT,
                special_requirements TEXT,
                predicted_discharge TIMESTAMP,
                discharge_ready BOOLEAN DEFAULT FALSE,
                discharge_notes TEXT,
                current_status TEXT DEFAULT 'admitted' CHECK (current_status IN ('admitted', 'discharged', 'transferred', 'deceased')),
                status_history TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Medical Equipment
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS medical_equipment (
                id SERIAL PRIMARY KEY,
                equipment_type TEXT NOT NULL,
                model TEXT,
                serial_number TEXT UNIQUE,
                status TEXT DEFAULT 'available' CHECK (status IN ('available', 'in_use', 'maintenance', 'out_of_service')),
                current_location INTEGER REFERENCES department_units(id),
                maintenance_due DATE,
                last_service_date DATE,
                capabilities TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Daily Clinical Load
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_clinical_load (
                id SERIAL PRIMARY KEY,
                report_date DATE NOT NULL UNIQUE,
                total_patients INTEGER DEFAULT 0 CHECK (total_patients >= 0),
                new_admissions INTEGER DEFAULT 0 CHECK (new_admissions >= 0),
                expected_discharges INTEGER DEFAULT 0 CHECK (expected_discharges >= 0),
                vent_patients INTEGER DEFAULT 0 CHECK (vent_patients >= 0),
                high_flow_o2_patients INTEGER DEFAULT 0 CHECK (high_flow_o2_patients >= 0),
                procedure_scheduled INTEGER DEFAULT 0 CHECK (procedure_scheduled >= 0),
                reported_by TEXT NOT NULL,
                clinical_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Predictive Alerts
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictive_alerts (
                id SERIAL PRIMARY KEY,
                alert_code TEXT UNIQUE NOT NULL,
                alert_type TEXT NOT NULL,
                alert_category TEXT,
                severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
                title TEXT NOT NULL,
                detailed_message TEXT NOT NULL,
                suggested_actions TEXT,
                target_units TEXT,
                target_roles TEXT,
                related_bed_id INTEGER REFERENCES enhanced_beds(id),
                related_staff_id INTEGER REFERENCES medical_staff(id),
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                predicted_event_time TIMESTAMP,
                confidence_score REAL DEFAULT 0.0 CHECK (confidence_score >= 0 AND confidence_score <= 1),
                acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_by TEXT,
                acknowledged_at TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                resolved_by TEXT,
                resolved_at TIMESTAMP,
                resolution_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Department Announcements
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS department_announcements (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'general' CHECK (message_type IN ('general', 'policy', 'urgent', 'alert')),
                target_audience TEXT DEFAULT 'all' CHECK (target_audience IN ('all', 'doctors', 'nurses', 'admin')),
                target_units TEXT,
                target_roles TEXT,
                priority_level TEXT DEFAULT 'normal' CHECK (priority_level IN ('low', 'normal', 'high', 'urgent')),
                effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                effective_until TIMESTAMP,
                posted_by TEXT NOT NULL,
                requires_acknowledgment BOOLEAN DEFAULT FALSE,
                acknowledgment_count INTEGER DEFAULT 0 CHECK (acknowledgment_count >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_medical_staff_active ON medical_staff(is_active, current_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_guardia_schedules_date ON guardia_schedules(schedule_date, shift_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_enhanced_beds_status ON enhanced_beds(status, room_code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patient_flow_current ON patient_flow(current_status, current_unit_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bed_audit_timestamp ON bed_audit_trail(timestamp DESC)")

        conn.commit()
        logger.info("✅ PostgreSQL tables created successfully!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Table creation failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

def tables_exist():
    """
    Check if all required tables exist in the database
    Returns: Boolean indicating if tables exist
    """
    conn = None
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        required_tables = [
            'hospital_system', 'department_units', 'medical_staff',
            'coverage_rules', 'guardia_schedules', 'enhanced_beds',
            'bed_audit_trail', 'patient_flow', 'medical_equipment',
            'daily_clinical_load', 'predictive_alerts', 'department_announcements'
        ]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        missing_tables = [table for table in required_tables if table not in existing_tables]
        
        if missing_tables:
            logger.warning(f"⚠️ Missing tables: {missing_tables}")
            return False
        else:
            logger.info("✅ All required tables exist")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error checking tables: {e}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    create_tables()