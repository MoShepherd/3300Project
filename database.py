import mysql.connector

dataBase = mysql.connector.connect(
    host="mysql",
    port=3306,
    user="user",
    passwd="password",
    database="landlorddb"
)

print("Successfully connected to MySQL!")

# preparing a cursor object
cursor = dataBase.cursor()

# creating database
cursor.execute("show databases")

for database in cursor:
    print(database)

cursor.close()
dataBase.close()