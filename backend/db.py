import mysql.connector

def get_db_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="bhavya@12345",
        database="hotel_reservation"
    )
    return connection