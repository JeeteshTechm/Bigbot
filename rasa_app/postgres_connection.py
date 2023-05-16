import psycopg2
from psycopg2 import Error

def insert_tar_file(file_path):
    connection = None  
    try:
        # Establish a connection to the PostgreSQL database
        connection = psycopg2.connect(
            user="rasa",
            password="rasa123",
            host="127.0.0.1",
            port="5432",
            database="rasadb"
        )
        cursor = connection.cursor()
        with open(file_path, 'rb') as file:
            file_data = file.read()
        insert_query = "INSERT INTO files (filename, data) VALUES (%s, %s);"

        cursor.execute(insert_query, (file_path, psycopg2.Binary(file_data)))

        connection.commit()

        print("Tar.gz file stored successfully.")

    except (Exception, Error) as error:
        print("Error while storing the tar.gz file:", error)

    finally:
        if connection:
            cursor.close()
            connection.close()

file_path = "./models/rasa_model.tar.gz"  
insert_tar_file(file_path)
