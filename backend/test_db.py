
from db import get_db_connection

try:
    connection = get_db_connection()

    if connection.is_connected():
        print("SUCCESS: Connected to MySQL!")

        cursor = connection.cursor()
        cursor.execute("SHOW TABLES")

        print("Tables in hotel_reservation database:")
        for table in cursor.fetchall():
            print(table)

        cursor.close()
        connection.close()
except Exception as error:
    print("Database connection failed:", error)
