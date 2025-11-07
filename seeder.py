"""
seeder.py - FINAL CORRECTED version with Enhanced Bed Management + Frontend Optimization
"""
import sqlite3
import datetime
import logging
import random
from datetime import date, timedelta

# Fix for Python 3.12 date adapter deprecation
def adapt_date_iso(val):
    """Adapt datetime.date and datetime.datetime to ISO format"""
    return val.isoformat()

sqlite3.register_adapter(datetime.date, adapt_date_iso)
sqlite3.register_adapter(datetime.datetime, adapt_date_iso)

logger = logging.getLogger(__name__)
DATABASE = 'pneumotrack_enterprise.db'

def seed_data():
    """Seed the database with initial data"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    try:
        # 1. Seed Hospital System Configuration
        logger.info("🏥 Seeding hospital system configuration...")
        cursor.execute("""
            INSERT INTO hospital_system 
            (hospital_name, chief_of_department, system_version, emergency_contact)
            VALUES (?, ?, ?, ?)
        """, (
            "Advanced Neumology & Pulmonary Center",
            "Dr. Maria Rodriguez", 
            "PneumoTrack Enterprise v4.0",
            "Internal: 5555, External: +1-555-0123"
        ))
        
        # 2. Seed Department Units
        logger.info("🏢 Seeding department units...")
        units = [
            ('Pulmonary ICU', 'PICU', 'Critical Care', '#e74c3c', '🏥', 'Main intensive care unit for pulmonary patients', 20, 15, 5, 15, 4, 1, 'operational', 1, '555-1001', 'Floor 3, West Wing'),
            ('General Pulmonology', 'GPULM', 'General Pulmonary', '#3498db', '🫁', 'General pulmonary care and consultations', 35, 28, 7, 5, 2, 0, 'operational', 1, '555-1002', 'Floor 2, Main Tower'),
            ('Bronchoscopy Suite', 'BSUITE', 'Procedural', '#9b59b6', '🔬', 'Bronchoscopy and interventional procedures', 8, 6, 2, 8, 3, 1, 'operational', 1, '555-1003', 'Floor 3, Procedure Wing'),
            ('Respiratory Isolation', 'ISOL', 'Infectious Disease', '#f39c12', '⚠️', 'Negative pressure isolation rooms', 12, 8, 4, 10, 12, 0, 'operational', 1, '555-1004', 'Floor 4, Isolation Wing'),
            ('Step-Down Unit', 'SDU', 'Intermediate Care', '#2ecc71', '📊', 'Intermediate care step-down unit', 25, 20, 5, 8, 1, 0, 'operational', 1, '555-1005', 'Floor 3, East Wing')
        ]
        
        cursor.executemany("""
            INSERT INTO department_units 
            (name, code, specialty, color_code, icon, description, total_beds, available_beds, standby_beds, 
             vent_capable_beds, negative_pressure_rooms, is_procedure_capable, status, is_active, unit_phone, unit_location)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, units)
        
        # 3. Seed Medical Staff - CORRECTED: 31 values for 31 columns
        logger.info("👨‍⚕️ Seeding medical staff...")
        staff_data = [
            # Chief and Senior Consultants (31 values each - CORRECTED)
            ('Maria', 'Rodriguez', 'Chief of Department', 'DR001', 'Pulmonology', 'Interventional', 'MD, FCCP', 'MED123001', 15, 1, '2,3', 'chief', 'm.rodriguez@hospital.org', '+1-555-0001', 'Admin Office: 5001', 1, 1, '2,3,4', 'available', 1, 1, 1, 'Bronchoscopy,Intubation,Thoracentesis', 1, 'flexible', None, None, None, None, 12, date.today() - timedelta(days=15)),
            ('James', 'Wilson', 'Senior Consultant', 'DR002', 'Critical Care', 'ICU Management', 'MD, FCCM', 'MED123002', 12, 1, '4,5', 'senior_consultant', 'j.wilson@hospital.org', '+1-555-0002', 'ICU Desk: 5002', 2, 1, '1,4', 'available', 1, 1, 1, 'Vent Management,Code Blue', 1, 'morning', None, None, None, None, 10, date.today() - timedelta(days=8)),
            ('Sarah', 'Chen', 'Senior Consultant', 'DR003', 'Interventional', 'Bronchoscopy', 'MD, FCCP', 'MED123003', 10, 3, '1,2', 'senior_consultant', 's.chen@hospital.org', '+1-555-0003', 'Bronch Suite: 5003', 3, 1, '1,3', 'available', 0, 1, 1, 'EBUS,Cryotherapy,Stent', 1, 'morning', None, None, None, None, 8, date.today() - timedelta(days=12)),
            
            # Consultants
            ('Robert', 'Johnson', 'Consultant', 'DR004', 'General Pulmonary', 'Sleep Medicine', 'MD', 'MED123004', 8, 2, '1,5', 'consultant', 'r.johnson@hospital.org', '+1-555-0004', 'Clinic: 5004', 4, 0, '2,5', 'available', 0, 0, 0, 'Sleep Studies,PFT', 1, 'evening', None, None, None, None, 6, date.today() - timedelta(days=20)),
            ('Emily', 'Davis', 'Consultant', 'DR005', 'Critical Care', 'ARDS', 'MD', 'MED123005', 7, 1, '4,5', 'consultant', 'e.davis@hospital.org', '+1-555-0005', 'ICU: 5005', 5, 1, '1,4', 'available', 1, 1, 0, 'ECMO,Vent Management', 1, 'night', None, None, None, None, 7, date.today() - timedelta(days=5)),
            ('Michael', 'Brown', 'Consultant', 'DR006', 'Interventional', 'Pleural', 'MD', 'MED123006', 6, 3, '1,2', 'consultant', 'm.brown@hospital.org', '+1-555-0006', 'Procedure: 5006', 6, 1, '3,4', 'available', 0, 1, 1, 'Thoracentesis,Chest Tube', 1, 'flexible', None, None, None, None, 5, date.today() - timedelta(days=25)),
            
            # Residents
            ('Lisa', 'Garcia', 'Resident', 'DR007', 'General Pulmonary', 'Fellow', 'MD', 'MED123007', 3, 2, '1,2,5', 'resident', 'l.garcia@hospital.org', '+1-555-0007', 'Resident Room: 5007', 7, 0, '1,2,4,5', 'available', 1, 1, 0, 'Basic Procedures', 1, 'flexible', None, None, None, None, 15, date.today() - timedelta(days=3)),
            ('David', 'Martinez', 'Resident', 'DR008', 'Critical Care', 'Fellow', 'MD', 'MED123008', 2, 1, '4,5', 'resident', 'd.martinez@hospital.org', '+1-555-0008', 'Resident Room: 5008', 8, 0, '1,4,5', 'available', 1, 1, 0, 'Vent Basics', 1, 'night', None, None, None, None, 12, date.today() - timedelta(days=7)),
            ('Amanda', 'Lee', 'Resident', 'DR009', 'Interventional', 'Fellow', 'MD', 'MED123009', 2, 3, '1,3', 'resident', 'a.lee@hospital.org', '+1-555-0009', 'Resident Room: 5009', 9, 0, '3,4', 'available', 0, 1, 1, 'Bronch Assist', 1, 'morning', None, None, None, None, 8, date.today() - timedelta(days=10))
        ]
        
        cursor.executemany("""
            INSERT INTO medical_staff 
            (first_name, last_name, title, staff_id, specialization, sub_specialization, qualifications, license_number, 
             years_experience, primary_unit_id, secondary_units, role, email, phone, emergency_contact, emergency_contact_priority,
             rapid_response_capable, backup_units, current_status, is_on_call, vent_trained, procedure_trained, competencies, is_active,
             preferred_shift, absence_type, absence_start, absence_end, absence_reason, guardia_count, last_guardia_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, staff_data)
        
        # 4. Seed Coverage Rules
        logger.info("📋 Seeding coverage rules...")
        coverage_rules = [
            (1, 'morning', 1, 2, 2, 1, 1),  # PICU morning
            (1, 'evening', 1, 2, 2, 1, 1),   # PICU evening  
            (1, 'night', 1, 2, 2, 1, 1),     # PICU night
            (2, 'morning', 0, 2, 1, 0, 0),   # General Pulmonology
            (2, 'evening', 0, 1, 1, 0, 0),
            (2, 'night', 0, 1, 1, 0, 0),
            (3, 'morning', 1, 1, 1, 1, 0),   # Bronchoscopy Suite
            (3, 'evening', 0, 1, 1, 1, 0),
            (4, 'morning', 0, 1, 1, 0, 0),   # Isolation
            (4, 'evening', 0, 1, 1, 0, 0),
            (4, 'night', 0, 1, 1, 0, 0),
            (5, 'morning', 0, 1, 1, 0, 0),   # Step-Down
            (5, 'evening', 0, 1, 1, 0, 0),
            (5, 'night', 0, 1, 1, 0, 0)
        ]
        
        cursor.executemany("""
            INSERT INTO coverage_rules 
            (unit_id, shift_type, min_senior_consultants, min_consultants, min_vent_trained, min_procedure_trained, is_critical_coverage)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, coverage_rules)
        
        # 5. Seed Guardia Schedules
        logger.info("📅 Seeding guardia schedules...")
        today = date.today()
        guardia_schedules = []
        
        # Create schedules for next 7 days
        for day in range(7):
            schedule_date = today + timedelta(days=day)
            
            # PICU shifts (unit_id = 1)
            guardia_schedules.append((1, schedule_date, 'morning', 1, 'scheduled', 'Primary coverage', 'system', 1, 1, 0, None))
            guardia_schedules.append((2, schedule_date, 'evening', 1, 'scheduled', 'Evening round', 'system', 1, 1, 0, None))
            guardia_schedules.append((5, schedule_date, 'night', 1, 'scheduled', 'Night coverage', 'system', 1, 1, 0, None))
            
            # General Pulmonology shifts (unit_id = 2)
            guardia_schedules.append((4, schedule_date, 'morning', 2, 'scheduled', 'Clinic duty', 'system', 1, 1, 0, None))
            guardia_schedules.append((6, schedule_date, 'evening', 2, 'scheduled', 'Ward round', 'system', 1, 1, 0, None))
            
            # Isolation unit shifts (unit_id = 4)
            guardia_schedules.append((8, schedule_date, 'night', 4, 'scheduled', 'Isolation coverage', 'system', 1, 1, 0, None))
        
        cursor.executemany("""
            INSERT INTO guardia_schedules 
            (staff_id, schedule_date, shift_type, unit_id, status, notes, created_by, conflict_checked, coverage_met, requires_attention, attention_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, guardia_schedules)
        
        # 6. Seed Absence Requests
        logger.info("🏖️ Seeding absence requests...")
        absence_requests = [
            (4, 'holiday', date.today() + timedelta(days=10), date.today() + timedelta(days=17), 'Family vacation', 'approved', 'Dr. Rodriguez', 'Covered by Dr. Davis', date.today()),
            (7, 'sick_leave', date.today() - timedelta(days=2), date.today() + timedelta(days=2), 'Seasonal flu', 'approved', 'Dr. Wilson', 'Resident coverage adjusted', date.today()),
            (5, 'emergency_leave', date.today() - timedelta(days=1), date.today() + timedelta(days=3), 'Family emergency', 'pending', None, 'Need coverage for ICU shifts', None),
            (9, 'maternity_leave', date.today() + timedelta(days=30), date.today() + timedelta(days=120), 'Maternity leave', 'approved', 'Dr. Rodriguez', 'Long-term coverage plan in place', date.today()),
            (6, 'paternity_leave', date.today() + timedelta(days=45), date.today() + timedelta(days=60), 'Paternity leave', 'pending', None, 'Short-term coverage needed', None),
            (8, 'other', date.today() + timedelta(days=15), date.today() + timedelta(days=16), 'Professional conference', 'approved', 'Dr. Chen', 'Single day coverage', date.today())
        ]
        
        cursor.executemany("""
            INSERT INTO absence_requests 
            (staff_id, request_type, start_date, end_date, reason, status, approved_by, coverage_notes, approved_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, absence_requests)
        
        # 7. Seed Enhanced Bed Management System (15 rooms × 4 beds = 60 beds)
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
                equipment = 'ventilator' if room <= 5 and bed == 1 else 'monitor,o2'  # First bed in first 5 rooms gets ventilator
                
                enhanced_beds_data.append((
                    f"H{room}", bed_code, display_name, status, 
                    None, clinical_needs, equipment, 'system', 'Initial setup'
                ))
        
        cursor.executemany("""
            INSERT INTO enhanced_beds 
            (room_code, bed_number, display_name, status, patient_id, clinical_needs, equipment, updated_by, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, enhanced_beds_data)
        
        # 8. Seed sample audit trail entries
        logger.info("📝 Seeding bed audit trail...")
        audit_data = []
        for bed_id in range(1, 21):  # Add audit entries for first 20 beds
            audit_data.append((
                bed_id, 'empty', 'occupied', 'system', 'Initial patient admission', None
            ))
        
        cursor.executemany("""
            INSERT INTO bed_audit_trail 
            (bed_id, old_status, new_status, updated_by, update_reason, patient_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, audit_data)
        
        # 9. Seed Patient Flow
        logger.info("👥 Seeding patient flow...")
        patient_data = []
        for i in range(1, 16):
            admission_date = date.today() - timedelta(days=random.randint(1, 10))
            predicted_discharge = admission_date + timedelta(days=random.randint(5, 21))
            patient_data.append((
                f"PT{2024:04d}{i:03d}", f"ANON{i:05d}", 'adult', 'COVID-19 ARDS', 'Hypertension,Diabetes', 
                'critical' if i <= 5 else 'guarded', i, 1, 2 if i <= 5 else 1, 'emergency', 'ER', 
                admission_date, 
                random.randint(5, 21), 'acute', 'Ventilator' if i <= 5 else 'High-flow O2',
                predicted_discharge, i > 10, '', 'admitted', 'Admission notes here'
            ))
        
        cursor.executemany("""
            INSERT INTO patient_flow 
            (patient_code, anonymous_id, age_group, primary_diagnosis, secondary_diagnoses, acuity_level, 
             current_bed_id, current_unit_id, attending_doctor_id, admission_type, admission_source, 
             admission_datetime, expected_length_of_stay, treatment_phase, special_requirements, 
             predicted_discharge, discharge_ready, discharge_notes, current_status, status_history)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, patient_data)
        
        # 10. Connect patients to beds realistically
        logger.info("🔗 Connecting patients to beds...")
        def seed_patient_bed_relationships(cursor):
            """Connect patients to beds realistically"""
            # Get first 20 patients and assign to occupied beds
            cursor.execute("SELECT id FROM patient_flow LIMIT 20")
            patients = cursor.fetchall()
            
            cursor.execute("SELECT id FROM enhanced_beds WHERE status = 'occupied' LIMIT 20")
            beds = cursor.fetchall()
            
            for i, (patient_id,) in enumerate(patients):
                if i < len(beds):
                    bed_id = beds[i][0]
                    cursor.execute(
                        "UPDATE enhanced_beds SET patient_id = ? WHERE id = ?",
                        (patient_id, bed_id)
                    )
            
            # Add sample audit trail for these assignments
            for i, (patient_id,) in enumerate(patients):
                if i < len(beds):
                    bed_id = beds[i][0]
                    cursor.execute("""
                        INSERT INTO bed_audit_trail 
                        (bed_id, old_status, new_status, updated_by, update_reason, patient_id)
                        VALUES (?, 'empty', 'occupied', 'seeder', 'Initial patient assignment', ?)
                    """, (bed_id, patient_id))
        
        seed_patient_bed_relationships(cursor)
        
        # 11. Seed Intelligent Beds (original system - keeping for compatibility)
        logger.info("🛏️ Seeding intelligent beds...")
        beds_data = []
        
        # PICU Beds (unit_id = 1)
        for i in range(1, 21):
            bed_type = 'icu' if i <= 15 else 'standard'
            status = 'available' if i > 15 else 'occupied'
            beds_data.append((
                f"PICU-{i:02d}", f"PICU Bed {i}", 1, f"Room {((i-1)//4)+1}", "Red Zone", f"{((i-1)%4)+1},{((i-1)//4)+1}",
                bed_type, "Ventilator,Monitor,O2", "Critical care", "Ventilation,Monitoring", 
                status, 0.95, 1, 'Wall O2', 'ICU', i <= 4, i <= 8, None, None, None, 45, 'routine', 0, None, 
                date.today() - timedelta(hours=12), date.today() + timedelta(days=30), None, 0, 0
            ))
        
        # General Pulmonology Beds (unit_id = 2)
        for i in range(1, 36):
            status = 'available' if i > 28 else 'occupied'
            beds_data.append((
                f"GP-{i:02d}", f"General Bed {i}", 2, f"Room {((i-1)//2)+1}", "Blue Zone", f"{((i-1)%2)+1},{((i-1)//2)+1}",
                'standard', "Monitor,O2", "General care", "O2 therapy,Monitoring", 
                status, 0.98, i <= 5, 'Wall O2', 'Basic', 0, 0, None, None, None, 30, 'routine', 0, None, 
                date.today() - timedelta(hours=6), date.today() + timedelta(days=60), None, 0, 0
            ))
        
        cursor.executemany("""
            INSERT INTO intelligent_beds 
            (bed_number, display_name, unit_id, room_number, zone, coordinates, bed_type, equipment, special_features, 
             clinical_capabilities, current_status, status_confidence, vent_capable, oxygen_type, monitor_type, 
             is_negative_pressure, is_procedure_ready, current_patient_id, occupied_since, expected_discharge, 
             estimated_cleaning_time, priority_level, requires_attention, attention_reason, last_cleaned, next_maintenance, 
             maintenance_notes, total_occupancy_hours, turnover_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, beds_data)
        
        # 12. Seed Medical Equipment
        logger.info("🔧 Seeding medical equipment...")
        equipment_data = [
            ('Ventilator', 'Hamilton-C1', 'VENT001', 'in_use', 1, date.today() + timedelta(days=60), date.today() - timedelta(days=30), 'ICU ventilation', 'Primary vent for PICU'),
            ('Ventilator', 'Hamilton-C1', 'VENT002', 'available', 1, date.today() + timedelta(days=90), date.today() - timedelta(days=15), 'ICU ventilation', 'Backup vent'),
            ('Bronchoscope', 'Olympus-BF190', 'BSC001', 'in_use', 3, date.today() + timedelta(days=30), date.today() - timedelta(days=7), 'Diagnostic bronchoscopy', 'Main bronchoscope'),
            ('Monitor', 'Philips-MX800', 'MON001', 'in_use', 1, date.today() + timedelta(days=180), date.today() - timedelta(days=60), 'Vital signs monitoring', 'ICU monitor'),
            ('High-Flow O2', 'Airvo-2', 'HFO001', 'available', 2, date.today() + timedelta(days=120), date.today() - timedelta(days=45), 'High flow oxygen therapy', 'Mobile unit')
        ]
        
        cursor.executemany("""
            INSERT INTO medical_equipment 
            (equipment_type, model, serial_number, status, current_location, maintenance_due, last_service_date, capabilities, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, equipment_data)
        
        # 13. Seed Daily Clinical Load
        logger.info("📊 Seeding daily clinical load...")
        for i in range(5):
            report_date = date.today() - timedelta(days=i)
            cursor.execute("""
                INSERT INTO daily_clinical_load 
                (report_date, total_patients, new_admissions, expected_discharges, vent_patients, high_flow_o2_patients, procedure_scheduled, reported_by, clinical_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        
        # 14. Seed Predictive Alerts
        logger.info("🚨 Seeding predictive alerts...")
        alerts = [
            ('ALERT001', 'staffing', 'coverage', 'medium', 'Evening Shift Coverage Gap', 
             'PICU evening shift has only 1 vent-trained staff scheduled', 'Review schedule, consider calling backup',
             '1', 'senior_consultant,consultant', 5, 2, date.today(), date.today() + timedelta(hours=2), 0.75, 0, None, None, 0, None, None, None),
            
            ('ALERT002', 'equipment', 'maintenance', 'low', 'Ventilator Maintenance Due', 
             'VENT001 due for routine maintenance in 60 days', 'Schedule maintenance before due date',
             '1', 'all', None, None, date.today(), date.today() + timedelta(days=45), 0.95, 1, 'Dr. Wilson', date.today(), 0, None, None, None),
            
            ('ALERT003', 'patient', 'acuity', 'high', 'Deteriorating Patient Cluster', 
             '3 patients in PICU showing similar deterioration patterns', 'Review cases, consider infection control measures',
             '1', 'chief,senior_consultant', 3, 1, date.today(), date.today() + timedelta(hours=6), 0.82, 0, None, None, 0, None, None, None)
        ]
        
        cursor.executemany("""
            INSERT INTO predictive_alerts 
            (alert_code, alert_type, alert_category, severity, title, detailed_message, suggested_actions, 
             target_units, target_roles, related_bed_id, related_staff_id, triggered_at, predicted_event_time, 
             confidence_score, acknowledged, acknowledged_by, acknowledged_at, resolved, resolved_by, resolved_at, resolution_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, alerts)
        
        # 15. Seed Department Announcements
        logger.info("📢 Seeding department announcements...")
        announcements = [
            ('New Bronchoscopy Protocol', 'All staff please review the updated bronchoscopy safety protocol in the shared folder.', 
             'policy', 'doctors', '3', 'consultant,resident', 'high', date.today(), date.today() + timedelta(days=30), 'Dr. Rodriguez', 1, 0),
            
            ('Quarterly Staff Meeting', 'Mandatory quarterly staff meeting next Friday at 3 PM in Conference Room A.', 
             'general', 'all', '1,2,3,4,5', 'all', 'normal', date.today(), date.today() + timedelta(days=14), 'Dr. Rodriguez', 0, 0),
            
            ('Ventilator Training', 'New ventilator equipment training session scheduled for next week.', 
             'urgent', 'doctors', '1', 'resident', 'high', date.today(), date.today() + timedelta(days=7), 'Dr. Wilson', 1, 0)
        ]
        
        cursor.executemany("""
            INSERT INTO department_announcements 
            (title, message, message_type, target_audience, target_units, target_roles, priority_level, 
             effective_from, effective_until, posted_by, requires_acknowledgment, acknowledgment_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, announcements)
        
        # 16. Validate seeded data meets frontend requirements
        logger.info("🔍 Validating seeded data for frontend compatibility...")
        def validate_seeded_data(cursor):
            """Validate that seeded data meets frontend requirements"""
            checks = [
                ("SELECT COUNT(*) FROM medical_staff WHERE is_active = 1", "Active staff"),
                ("SELECT COUNT(*) FROM enhanced_beds WHERE status IN ('occupied', 'available')", "Active beds"),
                ("SELECT COUNT(*) FROM guardia_schedules WHERE schedule_date >= DATE('now')", "Future schedules"),
                ("SELECT COUNT(*) FROM department_units WHERE is_active = 1", "Active units"),
                ("SELECT COUNT(*) FROM patient_flow WHERE current_status = 'admitted'", "Active patients")
            ]
            
            for query, description in checks:
                cursor.execute(query)
                count = cursor.fetchone()[0]
                logger.info(f"✅ {description}: {count}")
                
                if count == 0:
                    logger.warning(f"⚠️ No {description} found - frontend may show empty data")
        
        validate_seeded_data(cursor)
        
        conn.commit()
        logger.info("🎉 All data seeded successfully with enhanced bed management and frontend optimization!")
        
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"❌ Data seeding failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    seed_data()