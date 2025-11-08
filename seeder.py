import os
import psycopg2
from urllib.parse import urlparse

def seed_data():
    print("🔄 Seeding data...")
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found - cannot seed data")
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
        
        # Minimal sample data
        cursor.execute("INSERT INTO medical_staff (first_name, last_name, role) VALUES ('Dr. Maria', 'Gonzalez', 'Doctor')")
        cursor.execute("INSERT INTO medical_staff (first_name, last_name, role) VALUES ('Nurse Carlos', 'Rodriguez', 'Nurse')")
        
        cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number) VALUES ('ER-101', 'A')")
        cursor.execute("INSERT INTO enhanced_beds (room_code, bed_number) VALUES ('ER-102', 'B')")
        
        conn.commit()
        conn.close()
        print("✅ Data seeded successfully")
        return True
        
    except Exception as e:
        print(f"❌ Seeding failed: {e}")
        return False

# Remove the auto-execution during import
# if __name__ == '__main__':
#     seed_data()