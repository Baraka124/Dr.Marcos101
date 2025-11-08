import os
import psycopg2
from urllib.parse import urlparse

def seed_data():
    print("🔄 Seeding sample data...")
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found")
        return False
    
    try:
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port,
            sslmode='require'
        )
        cursor = conn.cursor()
        
        # Check if data exists
        cursor.execute("SELECT COUNT(*) FROM medical_staff")
        if cursor.fetchone()[0] > 0:
            print("✅ Data already exists")
            return True
        
        # Insert sample staff
        staff = [
            ('Maria', 'Gonzalez', 'Doctor', 'Emergency Medicine'),
            ('Carlos', 'Rodriguez', 'Nurse', 'Emergency Medicine'),
            ('Ana', 'Martinez', 'Doctor', 'Cardiology')
        ]
        
        for s in staff:
            cursor.execute(
                "INSERT INTO medical_staff (first_name, last_name, role, specialty) VALUES (%s, %s, %s, %s)",
                s
            )
        
        # Insert sample beds
        beds = [
            ('ER-101', 'A', 'empty'),
            ('ER-102', 'B', 'occupied'),
            ('ICU-201', '1', 'empty')
        ]
        
        for b in beds:
            cursor.execute(
                "INSERT INTO enhanced_beds (room_code, bed_number, status) VALUES (%s, %s, %s)",
                b
            )
        
        # Insert sample units
        units = [
            ('Emergency Room', 'ER'),
            ('Intensive Care Unit', 'ICU'),
            ('Cardiology', 'CARD')
        ]
        
        for u in units:
            cursor.execute(
                "INSERT INTO department_units (name, code) VALUES (%s, %s)",
                u
            )
        
        conn.commit()
        print("✅ Sample data seeded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error seeding data: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    seed_data()