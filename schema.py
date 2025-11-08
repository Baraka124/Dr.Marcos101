import os
import psycopg2
from urllib.parse import urlparse

def create_tables():
    print("🔄 Creating tables...")
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found - cannot create tables")
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
        
        tables = [
            """
            CREATE TABLE IF NOT EXISTS medical_staff (
                id SERIAL PRIMARY KEY,
                first_name VARCHAR(50),
                last_name VARCHAR(50),
                role VARCHAR(50),
                is_active BOOLEAN DEFAULT true
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS enhanced_beds (
                id SERIAL PRIMARY KEY,
                room_code VARCHAR(20),
                bed_number VARCHAR(10),
                status VARCHAR(20) DEFAULT 'empty'
            )
            """
        ]
        
        for table_sql in tables:
            cursor.execute(table_sql)
        
        conn.commit()
        conn.close()
        print("✅ Tables created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Table creation failed: {e}")
        return False

# Remove the auto-execution during import
# if __name__ == '__main__':
#     create_tables()