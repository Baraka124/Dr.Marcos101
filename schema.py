import os
import psycopg2
from urllib.parse import urlparse

def create_tables():
    print("🔄 Creating database tables...")
    
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
        
        # Simple tables
        tables = [
            """
            CREATE TABLE IF NOT EXISTS medical_staff (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(50) NOT NULL,
                last_name VARCHAR(50) NOT NULL,
                role VARCHAR(50) NOT NULL,
                specialty VARCHAR(100),
                is_active BOOLEAN DEFAULT true
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS enhanced_beds (
                id SERIAL PRIMARY KEY,
                room_code VARCHAR(20) NOT NULL,
                bed_number VARCHAR(10) NOT NULL,
                status VARCHAR(20) DEFAULT 'empty'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS department_units (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                code VARCHAR(20) UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT true
            )
            """
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        conn.commit()
        print("✅ Tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    create_tables()