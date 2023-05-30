import psycopg2

# Establish a connection to the PostgreSQL database
conn = psycopg2.connect(
    host="127.0.0.1",
    database="rasadb",
    user="rasa",
    password="rasa123"
)
# dialect="postgresql",
  

# Create a cursor object to interact with the database
cursor = conn.cursor()

# Execute the SQL query
cursor.execute("SELECT * FROM events WHERE sender_id='qwertyu';")

# Fetch all rows returned by the query
rows = cursor.fetchall()
print(rows)
# Process the retrieved data
for row in rows:
    # Access the columns by index or name
    column1_value = row[0]
    print("__________________",column1_value)
    column2_value = row[1]
    # ... process the data as needed

# Close the cursor and database connection
cursor.close()
conn.close()
# "d97341d8d9ba4cadb0e10d7bd950543a"
