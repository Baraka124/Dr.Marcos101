"""
schema.py - ENHANCED with all required columns + Bed Management + Performance Optimizations
"""
import sqlite3
import logging
import os

logger = logging.getLogger(__name__)
DATABASE = 'pneumotrack_enterprise.db'

def create_tables():
    """Create all database tables without any data"""
    # Remove existing database to ensure clean start
    if os.path.exists(DATABASE):
        os.remove(DATABASE)
        logger.info("🗑️ Removed existing database for clean start")
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # Hospital System Configuration
        cursor.execute("""
            CREATE TABLE hospital_system (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                hospital_name TEXT NOT NULL DEFAULT 'Advanced Neumology & Pulmonary Center',
                chief_of_department TEXT NOT NULL DEFAULT 'Dr. Maria Rodriguez',
                system_version TEXT NOT NULL DEFAULT 'PneumoTrack Enterprise v4.0',
                emergency_contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Department Units
        cursor.execute("""
            CREATE TABLE department_units (
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
            )
        """)
        
        # Medical Staff - COMPLETE with all app.py required columns
        cursor.execute("""
            CREATE TABLE medical_staff (
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
            )
        """)
        
        # Coverage Rules
        cursor.execute("""
            CREATE TABLE coverage_rules (
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
            )
        """)
        
        # Guardia Schedules - COMPLETE with all app.py required columns
        cursor.execute("""
            CREATE TABLE guardia_schedules (
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
            )
        """)
        
        # Shift Swap Requests
        cursor.execute("""
            CREATE TABLE shift_swap_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_shift_id INTEGER NOT NULL,
                requesting_staff_id INTEGER NOT NULL,
                potential_swap_staff_id INTEGER,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'cancelled')),
                reason TEXT,
                requires_chief_approval BOOLEAN DEFAULT 0,
                chief_approved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (original_shift_id) REFERENCES guardia_schedules (id),
                FOREIGN KEY (requesting_staff_id) REFERENCES medical_staff (id),
                FOREIGN KEY (potential_swap_staff_id) REFERENCES medical_staff (id)
            )
        """)
        
        # Absence Requests
        cursor.execute("""
            CREATE TABLE absence_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                staff_id INTEGER NOT NULL,
                request_type TEXT NOT NULL CHECK(request_type IN ('holiday', 'sick_leave', 'emergency_leave', 'maternity_leave', 'paternity_leave', 'other')),
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'approved', 'rejected', 'cancelled')),
                approved_by TEXT,
                approved_at TIMESTAMP,
                coverage_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (staff_id) REFERENCES medical_staff (id),
                CHECK (start_date <= end_date)
            )
        """)
        
        # Intelligent Beds
        cursor.execute("""
            CREATE TABLE intelligent_beds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bed_number TEXT UNIQUE NOT NULL,
                display_name TEXT,
                unit_id INTEGER NOT NULL,
                room_number TEXT,
                zone TEXT,
                coordinates TEXT,
                bed_type TEXT DEFAULT 'standard' CHECK(bed_type IN ('standard', 'icu', 'procedural', 'isolation')),
                equipment TEXT,
                special_features TEXT,
                clinical_capabilities TEXT,
                current_status TEXT DEFAULT 'available' CHECK(current_status IN ('available', 'occupied', 'cleaning', 'maintenance', 'reserved')),
                status_confidence REAL DEFAULT 1.0 CHECK(status_confidence >= 0 AND status_confidence <= 1),
                vent_capable BOOLEAN DEFAULT 0,
                oxygen_type TEXT CHECK(oxygen_type IN ('Wall O2', 'Portable', 'High Flow', 'None')),
                monitor_type TEXT CHECK(monitor_type IN ('Basic', 'Advanced', 'ICU', 'None')),
                is_negative_pressure BOOLEAN DEFAULT 0,
                is_procedure_ready BOOLEAN DEFAULT 0,
                current_patient_id INTEGER,
                occupied_since TIMESTAMP,
                expected_discharge TIMESTAMP,
                estimated_cleaning_time INTEGER DEFAULT 30 CHECK(estimated_cleaning_time >= 0),
                priority_level TEXT DEFAULT 'routine' CHECK(priority_level IN ('routine', 'urgent', 'critical')),
                requires_attention BOOLEAN DEFAULT 0,
                attention_reason TEXT,
                last_cleaned TIMESTAMP,
                next_maintenance TIMESTAMP,
                maintenance_notes TEXT,
                total_occupancy_hours REAL DEFAULT 0.0 CHECK(total_occupancy_hours >= 0),
                turnover_count INTEGER DEFAULT 0 CHECK(turnover_count >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (unit_id) REFERENCES department_units (id)
            )
        """)
        
        # ENHANCED BED MANAGEMENT SYSTEM - NEW TABLES
        cursor.execute("""
            CREATE TABLE enhanced_beds (
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
            )
        """)

        cursor.execute("""
            CREATE TABLE bed_audit_trail (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bed_id INTEGER,
                old_status TEXT,
                new_status TEXT,
                updated_by TEXT NOT NULL,
                update_reason TEXT,
                patient_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bed_id) REFERENCES enhanced_beds (id)
            )
        """)
        
        # Medical Equipment
        cursor.execute("""
            CREATE TABLE medical_equipment (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                equipment_type TEXT NOT NULL,
                model TEXT,
                serial_number TEXT UNIQUE,
                status TEXT DEFAULT 'available' CHECK(status IN ('available', 'in_use', 'maintenance', 'out_of_service')),
                current_location INTEGER,
                maintenance_due DATE,
                last_service_date DATE,
                capabilities TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (current_location) REFERENCES department_units (id)
            )
        """)
        
        # Daily Clinical Load
        cursor.execute("""
            CREATE TABLE daily_clinical_load (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                report_date DATE NOT NULL UNIQUE,
                total_patients INTEGER DEFAULT 0 CHECK(total_patients >= 0),
                new_admissions INTEGER DEFAULT 0 CHECK(new_admissions >= 0),
                expected_discharges INTEGER DEFAULT 0 CHECK(expected_discharges >= 0),
                vent_patients INTEGER DEFAULT 0 CHECK(vent_patients >= 0),
                high_flow_o2_patients INTEGER DEFAULT 0 CHECK(high_flow_o2_patients >= 0),
                procedure_scheduled INTEGER DEFAULT 0 CHECK(procedure_scheduled >= 0),
                reported_by TEXT NOT NULL,
                clinical_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Patient Flow
        cursor.execute("""
            CREATE TABLE patient_flow (
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
                FOREIGN KEY (current_bed_id) REFERENCES intelligent_beds (id),
                FOREIGN KEY (current_unit_id) REFERENCES department_units (id),
                FOREIGN KEY (attending_doctor_id) REFERENCES medical_staff (id)
            )
        """)
        
        # Predictive Alerts
        cursor.execute("""
            CREATE TABLE predictive_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_code TEXT UNIQUE NOT NULL,
                alert_type TEXT NOT NULL,
                alert_category TEXT,
                severity TEXT DEFAULT 'medium' CHECK(severity IN ('low', 'medium', 'high', 'critical')),
                title TEXT NOT NULL,
                detailed_message TEXT NOT NULL,
                suggested_actions TEXT,
                target_units TEXT,
                target_roles TEXT,
                related_bed_id INTEGER,
                related_staff_id INTEGER,
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                predicted_event_time TIMESTAMP,
                confidence_score REAL DEFAULT 0.0 CHECK(confidence_score >= 0 AND confidence_score <= 1),
                acknowledged BOOLEAN DEFAULT 0,
                acknowledged_by TEXT,
                acknowledged_at TIMESTAMP,
                resolved BOOLEAN DEFAULT 0,
                resolved_by TEXT,
                resolved_at TIMESTAMP,
                resolution_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (related_bed_id) REFERENCES intelligent_beds (id),
                FOREIGN KEY (related_staff_id) REFERENCES medical_staff (id)
            )
        """)
        
        # Department Announcements
        cursor.execute("""
            CREATE TABLE department_announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                message_type TEXT DEFAULT 'general' CHECK(message_type IN ('general', 'policy', 'urgent', 'alert')),
                target_audience TEXT DEFAULT 'all' CHECK(target_audience IN ('all', 'doctors', 'nurses', 'admin')),
                target_units TEXT,
                target_roles TEXT,
                priority_level TEXT DEFAULT 'normal' CHECK(priority_level IN ('low', 'normal', 'high', 'urgent')),
                effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                effective_until TIMESTAMP,
                posted_by TEXT NOT NULL,
                requires_acknowledgment BOOLEAN DEFAULT 0,
                acknowledgment_count INTEGER DEFAULT 0 CHECK(acknowledgment_count >= 0),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create basic indexes
        indexes = [
            "CREATE INDEX idx_beds_unit_status ON intelligent_beds(unit_id, current_status)",
            "CREATE INDEX idx_staff_status ON medical_staff(current_status, is_active)",
            "CREATE INDEX idx_guardia_date ON guardia_schedules(schedule_date, shift_type)",
            "CREATE INDEX idx_enhanced_beds_room ON enhanced_beds(room_code, bed_number)",
            "CREATE INDEX idx_enhanced_beds_status ON enhanced_beds(status)",
            "CREATE INDEX idx_bed_audit_timestamp ON bed_audit_trail(timestamp)"
        ]
        
        # Performance indexes for frontend
        performance_indexes = [
            "CREATE INDEX idx_staff_frontend ON medical_staff(is_active, current_status, primary_unit_id)",
            "CREATE INDEX idx_guardia_frontend ON guardia_schedules(schedule_date, status, unit_id)",
            "CREATE INDEX idx_beds_frontend ON enhanced_beds(status, room_code)",
            "CREATE INDEX idx_announcements_active ON department_announcements(effective_from, effective_until, priority_level)",
            "CREATE INDEX idx_patient_current ON patient_flow(current_status, current_unit_id)",
            "CREATE INDEX idx_alerts_active ON predictive_alerts(resolved, severity, triggered_at)",
            "CREATE INDEX idx_bed_audit_recent ON bed_audit_trail(bed_id, timestamp DESC)",
            "CREATE INDEX idx_equipment_status ON medical_equipment(status, current_location)"
        ]
        
        for index in indexes + performance_indexes:
            try:
                cursor.execute(index)
            except sqlite3.Error as e:
                logger.warning(f"Index creation skipped: {e}")
        
        # Create frontend views
        frontend_views = [
            """
            CREATE VIEW staff_schedule_view AS
            SELECT 
                gs.id,
                gs.schedule_date,
                gs.shift_type,
                gs.status,
                ms.first_name || ' ' || ms.last_name AS staff_name,
                ms.staff_id,
                ms.role,
                du.name AS unit_name,
                du.code AS unit_code
            FROM guardia_schedules gs
            JOIN medical_staff ms ON gs.staff_id = ms.id
            JOIN department_units du ON gs.unit_id = du.id
            WHERE ms.is_active = 1
            """,
            
            """
            CREATE VIEW bed_management_view AS
            SELECT 
                eb.id,
                eb.room_code,
                eb.bed_number,
                eb.display_name,
                eb.status,
                eb.clinical_needs,
                eb.equipment,
                eb.last_updated,
                pf.patient_code,
                pf.acuity_level,
                ms.first_name || ' ' || ms.last_name AS attending_doctor
            FROM enhanced_beds eb
            LEFT JOIN patient_flow pf ON eb.patient_id = pf.id
            LEFT JOIN medical_staff ms ON pf.attending_doctor_id = ms.id
            """,
            
            """
            CREATE VIEW department_coverage_view AS
            SELECT 
                cr.unit_id,
                du.name AS unit_name,
                cr.shift_type,
                cr.min_senior_consultants,
                cr.min_consultants,
                COUNT(CASE WHEN ms.role = 'senior_consultant' THEN 1 END) AS scheduled_seniors,
                COUNT(CASE WHEN ms.role IN ('consultant', 'senior_consultant') THEN 1 END) AS scheduled_total
            FROM coverage_rules cr
            JOIN department_units du ON cr.unit_id = du.id
            LEFT JOIN guardia_schedules gs ON cr.unit_id = gs.unit_id AND cr.shift_type = gs.shift_type
            LEFT JOIN medical_staff ms ON gs.staff_id = ms.id
            WHERE gs.schedule_date = CURRENT_DATE
            GROUP BY cr.unit_id, cr.shift_type
            """
        ]
        
        for view in frontend_views:
            try:
                cursor.execute(view)
            except sqlite3.Error as e:
                logger.warning(f"View creation skipped: {e}")
        
        # Add data validation triggers
        cursor.execute("""
            CREATE TRIGGER validate_bed_assignment 
            BEFORE UPDATE ON enhanced_beds
            FOR EACH ROW
            WHEN NEW.patient_id IS NOT NULL AND NEW.status != 'occupied'
            BEGIN
                SELECT RAISE(ABORT, 'Bed with patient must be occupied status');
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER validate_staff_absence 
            BEFORE UPDATE ON medical_staff
            FOR EACH ROW
            WHEN NEW.absence_type IS NOT NULL AND (NEW.absence_start IS NULL OR NEW.absence_end IS NULL)
            BEGIN
                SELECT RAISE(ABORT, 'Absence requires both start and end dates');
            END;
        """)
        
        conn.commit()
        logger.info("✅ Enhanced database schema with bed management created successfully!")
        
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"❌ Schema creation failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_tables()