"""
seeder.py - PostgreSQL Data Seeding
Populates database with comprehensive sample data for hospital management system
"""

import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import random
from datetime import date, timedelta

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
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        raise

def is_database_empty():
    """
    Check if database has any data
    Returns: Boolean indicating if database is empty
    """
    conn = None
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        # Check if any medical staff exist
        cursor.execute("SELECT COUNT(*) FROM medical_staff")
        staff_count = cursor.fetchone()[0]
        
        # Check if any beds exist
        cursor.execute("SELECT COUNT(*) FROM enhanced_beds")
        beds_count = cursor.fetchone()[0]
        
        # Check if any units exist
        cursor.execute("SELECT COUNT(*) FROM department_units")
        units_count = cursor.fetchone()[0]
        
        is_empty = staff_count == 0 and beds_count == 0 and units_count == 0
        logger.info(f"📊 Database empty check - Staff: {staff_count}, Beds: {beds_count}, Units: {units_count}")
        
        return is_empty
        
    except Exception as e:
        logger.error(f"❌ Error checking database emptiness: {e}")
        return True  # Assume empty if we can't check
    finally:
        if conn:
            conn.close()

def seed_data():
    """
    Populate database with comprehensive sample data
    Only seeds if database is empty
    """
    if not is_database_empty():
        logger.info("📊 Database already has data, skipping seeding")
        return
    
    conn = None
    try:
        conn = get_database_connection()
        cursor = conn.cursor()
        
        logger.info("🌱 Starting database seeding...")
        
        # 1. Seed Hospital System Configuration
        logger.info("🏥 Seeding hospital system configuration...")
        cursor.execute("""
            INSERT INTO hospital_system 
            (hospital_name, chief_of_department, system_version, emergency_contact)
            VALUES (%s, %s, %s, %s)
        """, (
            "Advanced Neumology & Pulmonary Center",
            "Dr. Maria Rodriguez", 
            "PneumoTrack Enterprise v4.0",
            "Internal: 5555, External: +1-555-0123"
        ))
        
        # 2. Seed Department Units
        logger.info("🏢 Seeding department units...")
        units_data = [
            ('Pulmonary ICU', 'PICU', 'Critical Care', '#e74c3c', '🏥', 'Main intensive care unit for pulmonary patients', 20, 15, 5, 15, 4, True, 'operational', True, '555-1001', 'Floor 3, West Wing'),
            ('General Pulmonology', 'GPULM', 'General Pulmonary', '#3498db', '🫁', 'General pulmonary care and consultations', 35, 28, 7, 5, 2, False, 'operational', True, '555-1002', 'Floor 2, Main Tower'),
            ('Bronchoscopy Suite', 'BSUITE', 'Procedural', '#9b59b6', '🔬', 'Bronchoscopy and interventional procedures', 8, 6, 2, 8, 3, True, 'operational', True, '555-1003', 'Floor 3, Procedure Wing'),
            ('Respiratory Isolation', 'ISOL', 'Infectious Disease', '#f39c12', '⚠️', 'Negative pressure isolation rooms', 12, 8, 4, 10, 12, False, 'operational', True, '555-1004', 'Floor 4, Isolation Wing'),
            ('Step-Down Unit', 'SDU', 'Intermediate Care', '#2ecc71', '📊', 'Intermediate care step-down unit', 25, 20, 5, 8, 1, False, 'operational', True, '555-1005', 'Floor 3, East Wing')
        ]
        
        for unit in units_data:
            cursor.execute("""
                INSERT INTO department_units 
                (name, code, specialty, color_code, icon, description, total_beds, available_beds, standby_beds, 
                 vent_capable_beds, negative_pressure_rooms, is_procedure_capable, status, is_active, unit_phone, unit_location)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, unit)
        
        # 3. Seed Medical Staff
        logger.info("👨‍⚕️ Seeding medical staff...")
        staff_data = [
            # Chief and Senior Consultants
            ('Maria', 'Rodriguez', 'Chief of Department', 'DR001', 'Pulmonology', 'Interventional', 'MD, FCCP', 'MED123001', 15, 1, '2,3', 'chief', 'm.rodriguez@hospital.org', '+1-555-0001', 'Admin Office: 5001', 1, True, '2,3,4', 'available', True, True, True, 'Bronchoscopy,Intubation,Thoracentesis', True, 'flexible', None, None, None, None, 12, date.today() - timedelta(days=15)),
            ('James', 'Wilson', 'Senior Consultant', 'DR002', 'Critical Care', 'ICU Management', 'MD, FCCM', 'MED123002', 12, 1, '4,5', 'senior_consultant', 'j.wilson@hospital.org', '+1-555-0002', 'ICU Desk: 5002', 2, True, '1,4', 'available', True, True, True, 'Vent Management,Code Blue', True, 'morning', None, None, None, None, 10, date.today() - timedelta(days=8)),
            ('Sarah', 'Chen', 'Senior Consultant', 'DR003', 'Interventional', 'Bronchoscopy', 'MD, FCCP', 'MED123003', 10, 3, '1,2', 'senior_consultant', 's.chen@hospital.org', '+1-555-0003', 'Bronch Suite: 5003', 3, True, '1,3', 'available', False, True, True, 'EBUS,Cryotherapy,Stent', True, 'morning', None, None, None, None, 8, date.today() - timedelta(days=12)),
            
            # Consultants
            ('Robert', 'Johnson', 'Consultant', 'DR004', 'General Pulmonary', 'Sleep Medicine', 'MD', 'MED123004', 8, 2, '1,5', 'consultant', 'r.johnson@hospital.org', '+1-555-0004', 'Clinic: 5004', 4, False, '2,5', 'available', False, False, False, 'Sleep Studies,PFT', True, 'evening', None, None, None, None, 6, date.today() - timedelta(days=20)),
            ('Emily', 'Davis', 'Consultant', 'DR005', 'Critical Care', 'ARDS', 'MD', 'MED123005', 7, 1, '4,5', 'consultant', 'e.davis@hospital.org', '+1-555-0005', 'ICU: 5005', 5, True, '1,4', 'available', True, True, False, 'ECMO,Vent Management', True, 'night', None, None, None, None, 7, date.today() - timedelta(days=5)),
            ('Michael', 'Brown', 'Consultant', 'DR006', 'Interventional', 'Pleural', 'MD', 'MED123006', 6, 3, '1,2', 'consultant', 'm.brown@hospital.org', '+1-555-0006', 'Procedure: 5006', 6, True, '3,4', 'available', False, True, True, 'Thoracentesis,Chest Tube', True, 'flexible', None, None, None, None, 5, date.today() - timedelta(days=25)),
            
            # Residents
            ('Lisa', 'Garcia', 'Resident', 'DR007', 'General Pulmonary', 'Fellow', 'MD', 'MED123007', 3, 2, '1,2,5', 'resident', 'l.garcia@hospital.org', '+1-555-0007', 'Resident Room: 5007', 7, False, '1,2,4,5', 'available', True, True, False, 'Basic Procedures', True, 'flexible', None, None, None, None, 15, date.today() - timedelta(days=3)),
            ('David', 'Martinez', 'Resident', 'DR008', 'Critical Care', 'Fellow', 'MD', 'MED123008', 2, 1, '4,5', 'resident', 'd.martinez@hospital.org', '+1-555-0008', 'Resident Room: 5008', 8, False, '1,4,5', 'available', True, True, False, 'Vent Basics', True, 'night', None, None, None, None, 12, date.today() - timedelta(days=7)),
            ('Amanda', 'Lee', 'Resident', 'DR009', 'Interventional', 'Fellow', 'MD', 'MED123009', 2, 3, '1,3', 'resident', 'a.lee@hospital.org', '+1-555-0009', 'Resident Room: 5009', 9, False, '3,4', 'available', False, True, True, 'Bronch Assist', True, 'morning', None, None, None, None, 8, date.today() - timedelta(days=10))
        ]
        
        for staff in staff_data:
            cursor.execute("""
                INSERT INTO medical_staff 
                (first_name, last_name, title, staff_id, specialization, sub_specialization, qualifications, license_number, 
                 years_experience, primary_unit_id, secondary_units, role, email, phone, emergency_contact, emergency_contact_priority,
                 rapid_response_capable, backup_units, current_status, is_on_call, vent_trained, procedure_trained, competencies, is_active,
                 preferred_shift, absence_type, absence_start, absence_end, absence_reason, guardia_count, last_guardia_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, staff)
        
        # 4. Seed Coverage Rules
        logger.info("📋 Seeding coverage rules...")
        coverage_rules = [
            (1, 'morning', 1, 2, 2, 1, True),
            (1, 'evening', 1, 2, 2, 1, True),
            (1, 'night', 1, 2, 2, 1, True),
            (2, 'morning', 0, 2, 1, 0, False),
            (2, 'evening', 0, 1, 1, 0, False),
            (2, 'night', 0, 1, 1, 0, False),
            (3, 'morning', 1, 1, 1, 1, False),
            (3, 'evening', 0, 1, 1, 1, False),
            (4, 'morning', 0, 1, 1, 0, False),
            (4, 'evening', 0, 1, 1, 0, False),
            (4, 'night', 0, 1, 1, 0, False),
            (5, 'morning', 0, 1, 1, 0, False),
            (5, 'evening', 0, 1, 1, 0, False),
            (5, 'night', 0, 1, 1, 0, False)
        ]
        
        for rule in coverage_rules:
            cursor.execute("""
                INSERT INTO coverage_rules 
                (unit_id, shift_type, min_senior_consultants, min_consultants, min_vent_trained, min_procedure_trained, is_critical_coverage)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, rule)
        
        # 5. Seed Guardia Schedules
        logger.info("📅 Seeding guardia schedules...")
        today = date.today()
        guardia_schedules = []
        
        # Create schedules for next 7 days
        for day in range(7):
            schedule_date = today + timedelta(days=day)
            
            # PICU shifts (unit_id = 1)
            guardia_schedules.append((1, schedule_date, 'morning', 1, 'scheduled', 'Primary coverage', 'system', True, True, False, None))
            guardia_schedules.append((2, schedule_date, 'evening', 1, 'scheduled', 'Evening round', 'system', True, True, False, None))
            guardia_schedules.append((5, schedule_date, 'night', 1, 'scheduled', 'Night coverage', 'system', True, True, False, None))
            
            # General Pulmonology shifts (unit_id = 2)
            guardia_schedules.append((4, schedule_date, 'morning', 2, 'scheduled', 'Clinic duty', 'system', True, True, False, None))
            guardia_schedules.append((6, schedule_date, 'evening', 2, 'scheduled', 'Ward round', 'system', True, True, False, None))
            
            # Isolation unit shifts (unit_id = 4)
            guardia_schedules.append((8, schedule_date, 'night', 4, 'scheduled', 'Isolation coverage', 'system', True, True, False, None))
        
        for schedule in guardia_schedules:
            cursor.execute("""
                INSERT INTO guardia_schedules 
                (staff_id, schedule_date, shift_type, unit_id, status, notes, created_by, conflict_checked, coverage_met, requires_attention, attention_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, schedule)
        
        # 6. Seed Enhanced Bed Management System (15 rooms × 4 beds = 60 beds)
        logger.info("🛏️ Seeding enhanced bed management system...")
        enhanced_beds_data = []
        
        # Create 15 rooms (H1-H15) with 4 beds each (BH11-BH154)
        for room in range(1, 16):
            for bed in range(1, 5):
                bed_code = f"BH{room}{bed}"
                display_name = f"Bed {bed} - H{room}"
                
                # Randomly assign some beds as occupied for realism
                status = 'occupied' if random.random() < 0.4 else 'empty'
                clinical_needs = 'oxygen,monitoring' if status == 'occupied' else None
                equipment = 'ventilator' if room <= 5 and bed == 1 else 'monitor,o2'
                
                enhanced_beds_data.append((
                    f"H{room}", bed_code, display_name, status, 
                    None, clinical_needs, equipment, 'system', 'Initial setup'
                ))
        
        for bed in enhanced_beds_data:
            cursor.execute("""
                INSERT INTO enhanced_beds 
                (room_code, bed_number, display_name, status, patient_id, clinical_needs, equipment, updated_by, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, bed)
        
        # 7. Seed Patient Flow
        logger.info("👥 Seeding patient flow...")
        patient_data = []
        for i in range(1, 16):
            admission_date = date.today() - timedelta(days=random.randint(1, 10))
            predicted_discharge = admission_date + timedelta(days=random.randint(5, 21))
            
            # Assign to actual bed IDs (1-15 for first 15 patients)
            current_bed_id = i if i <= 15 else None
            
            patient_data.append((
                f"PT{2024:04d}{i:03d}", f"ANON{i:05d}", 'adult', 'COVID-19 ARDS', 'Hypertension,Diabetes', 
                'critical' if i <= 5 else 'guarded', current_bed_id, 1, 2 if i <= 5 else 1, 'emergency', 'ER', 
                admission_date, 
                random.randint(5, 21), 'acute', 'Ventilator' if i <= 5 else 'High-flow O2',
                predicted_discharge, i > 10, '', 'admitted', 'Admission notes here'
            ))
        
        for patient in patient_data:
            cursor.execute("""
                INSERT INTO patient_flow 
                (patient_code, anonymous_id, age_group, primary_diagnosis, secondary_diagnoses, acuity_level, 
                 current_bed_id, current_unit_id, attending_doctor_id, admission_type, admission_source, 
                 admission_datetime, expected_length_of_stay, treatment_phase, special_requirements, 
                 predicted_discharge, discharge_ready, discharge_notes, current_status, status_history)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, patient)
        
        # 8. Connect patients to beds realistically
        logger.info("🔗 Connecting patients to beds...")
        for i in range(1, 16):
            if i <= 15:  # First 15 patients get beds
                cursor.execute("""
                    UPDATE enhanced_beds SET patient_id = %s, status = 'occupied' 
                    WHERE id = %s
                """, (i, i))
                
                # Add audit trail for these assignments
                cursor.execute("""
                    INSERT INTO bed_audit_trail 
                    (bed_id, old_status, new_status, updated_by, update_reason, patient_id)
                    VALUES (%s, 'empty', 'occupied', 'seeder', 'Initial patient assignment', %s)
                """, (i, i))
        
        # 9. Seed Medical Equipment
        logger.info("🔧 Seeding medical equipment...")
        equipment_data = [
            ('Ventilator', 'Hamilton-C1', 'VENT001', 'in_use', 1, date.today() + timedelta(days=60), date.today() - timedelta(days=30), 'ICU ventilation', 'Primary vent for PICU'),
            ('Ventilator', 'Hamilton-C1', 'VENT002', 'available', 1, date.today() + timedelta(days=90), date.today() - timedelta(days=15), 'ICU ventilation', 'Backup vent'),
            ('Bronchoscope', 'Olympus-BF190', 'BSC001', 'in_use', 3, date.today() + timedelta(days=30), date.today() - timedelta(days=7), 'Diagnostic bronchoscopy', 'Main bronchoscope'),
            ('Monitor', 'Philips-MX800', 'MON001', 'in_use', 1, date.today() + timedelta(days=180), date.today() - timedelta(days=60), 'Vital signs monitoring', 'ICU monitor'),
            ('High-Flow O2', 'Airvo-2', 'HFO001', 'available', 2, date.today() + timedelta(days=120), date.today() - timedelta(days=45), 'High flow oxygen therapy', 'Mobile unit')
        ]
        
        for equipment in equipment_data:
            cursor.execute("""
                INSERT INTO medical_equipment 
                (equipment_type, model, serial_number, status, current_location, maintenance_due, last_service_date, capabilities, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, equipment)
        
        # 10. Seed Daily Clinical Load
        logger.info("📊 Seeding daily clinical load...")
        for i in range(5):
            report_date = date.today() - timedelta(days=i)
            cursor.execute("""
                INSERT INTO daily_clinical_load 
                (report_date, total_patients, new_admissions, expected_discharges, vent_patients, high_flow_o2_patients, procedure_scheduled, reported_by, clinical_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                report_date, 
                45 - i*2,  # Decreasing patient count
                3 + (i % 2), 
                2 + (i % 3),
                8 - (i % 3),
                12 - i,
                4 - (i % 2),
                'Dr. Rodriguez' if i == 0 else 'Dr. Wilson',
                f"Standard daily load. Trend: {'stable' if i < 2 else 'improving'}"
            ))
        
        # 11. Seed Predictive Alerts
        logger.info("🚨 Seeding predictive alerts...")
        alerts = [
            ('ALERT001', 'staffing', 'coverage', 'medium', 'Evening Shift Coverage Gap', 
             'PICU evening shift has only 1 vent-trained staff scheduled', 'Review schedule, consider calling backup',
             '1', 'senior_consultant,consultant', 5, 2, date.today(), date.today() + timedelta(hours=2), 0.75, False, None, None, False, None, None, None),
            
            ('ALERT002', 'equipment', 'maintenance', 'low', 'Ventilator Maintenance Due', 
             'VENT001 due for routine maintenance in 60 days', 'Schedule maintenance before due date',
             '1', 'all', None, None, date.today(), date.today() + timedelta(days=45), 0.95, True, 'Dr. Wilson', date.today(), False, None, None, None),
            
            ('ALERT003', 'patient', 'acuity', 'high', 'Deteriorating Patient Cluster', 
             '3 patients in PICU showing similar deterioration patterns', 'Review cases, consider infection control measures',
             '1', 'chief,senior_consultant', 3, 1, date.today(), date.today() + timedelta(hours=6), 0.82, False, None, None, False, None, None, None)
        ]
        
        for alert in alerts:
            cursor.execute("""
                INSERT INTO predictive_alerts 
                (alert_code, alert_type, alert_category, severity, title, detailed_message, suggested_actions, 
                 target_units, target_roles, related_bed_id, related_staff_id, triggered_at, predicted_event_time, 
                 confidence_score, acknowledged, acknowledged_by, acknowledged_at, resolved, resolved_by, resolved_at, resolution_notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, alert)
        
        # 12. Seed Department Announcements
        logger.info("📢 Seeding department announcements...")
        announcements = [
            ('New Bronchoscopy Protocol', 'All staff please review the updated bronchoscopy safety protocol in the shared folder.', 
             'policy', 'doctors', '3', 'consultant,resident', 'high', date.today(), date.today() + timedelta(days=30), 'Dr. Rodriguez', True, 0),
            
            ('Quarterly Staff Meeting', 'Mandatory quarterly staff meeting next Friday at 3 PM in Conference Room A.', 
             'general', 'all', '1,2,3,4,5', 'all', 'normal', date.today(), date.today() + timedelta(days=14), 'Dr. Rodriguez', False, 0),
            
            ('Ventilator Training', 'New ventilator equipment training session scheduled for next week.', 
             'urgent', 'doctors', '1', 'resident', 'high', date.today(), date.today() + timedelta(days=7), 'Dr. Wilson', True, 0)
        ]
        
        for announcement in announcements:
            cursor.execute("""
                INSERT INTO department_announcements 
                (title, message, message_type, target_audience, target_units, target_roles, priority_level, 
                 effective_from, effective_until, posted_by, requires_acknowledgment, acknowledgment_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, announcement)
        
        conn.commit()
        logger.info("🎉 Database seeded successfully with comprehensive sample data!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Data seeding failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    seed_data()