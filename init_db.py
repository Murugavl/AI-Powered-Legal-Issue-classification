
import os
import psycopg2
from dotenv import load_dotenv

def main():
    # Load environment variables
    load_dotenv(override=True)
    
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "sql123")
    dbname = os.getenv("POSTGRES_DB", "legal_db")
    
    # Read the SQL file
    try:
        with open("DATABASE_SCHEMA.sql", "r") as f:
            sql_commands = f.read()
    except Exception as e:
        print(f"Failed to read DATABASE_SCHEMA.sql: {e}")
        return

    try:
        # Establish a connection
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            dbname=dbname,
            port=port
        )
        print("Connected to database.")
        
        # Execute commands
        with conn.cursor() as cursor:
            # We assume the file contains a long string of SQL commands.
            # psycopg2 should handle multiple statements in execute().
            cursor.execute(sql_commands)
            
        conn.commit()
        conn.close()
        print("Tables created successfully.")
        
    except psycopg2.Error as e:
        print(f"Error creating tables: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()
