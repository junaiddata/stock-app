from flask import Flask, request, render_template, redirect, url_for
import sqlite3
import pandas as pd
import os

app = Flask(__name__)

# Define the SQLite database file path
DB_PATH = "stock_data5.db"

# Function to initialize (or re-initialize) the database with the Excel data
def initialize_db(force_update=False):
    # If force_update is True, delete the existing database file
    if force_update and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Existing database deleted for update.")

    # If the database exists (and not forcing update), do nothing
    if os.path.exists(DB_PATH):
        print("Database already exists.")
        return

    # Read Excel data
    df = pd.read_excel('uploads/stock_data1.xlsx')
    print("Data from Excel:", df.head())

    # Clean column names and data
    df.columns = df.columns.str.strip()  # Remove extra spaces from column names
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)  # Strip spaces from string columns
    df['ItemCode'] = df['ItemCode'].astype(str)  # Ensure ItemCode is a string
    
    # Ensure the UPC column is a string, if it exists
    if "Upc Code" in df.columns:
        df["Upc Code"] = df["Upc Code"].astype(str)

    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table with six columns
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_items (
            "ItemCode" TEXT,
            "Upc Code" TEXT,
            "Description" TEXT,
            "Manufacturer Name" TEXT,
            "Warehouse Code" TEXT,
            "Stock Quantity" INTEGER
        )
    ''')
    print("Table created or already exists.")

    # Insert data into the table (replace any existing data)
    df.to_sql('stock_items', conn, if_exists='replace', index=False)
    print("Data inserted into database successfully.")

    # Verify row count
    cursor.execute("SELECT COUNT(*) FROM stock_items")
    row_count = cursor.fetchone()[0]
    print(f"Rows inserted: {row_count}")

    conn.commit()
    conn.close()

# Initialize the database at startup (without forcing update)
initialize_db()

# For debugging: list the tables in the database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
print("Tables in DB:", cursor.fetchall())
conn.close()

@app.route("/", methods=["GET", "POST"])
def index():
    results = None
    query = ""

    # Debug: Print the first 10 records of the database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_items LIMIT 10")
    print("First 10 records:", cursor.fetchall())
    conn.close()

    if request.method == "POST":
        query = request.form.get("query", "").strip().lower()
        if query:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            # Search by ItemCode, Upc Code, Description, or Manufacturer Name (all case-insensitive)
            cursor.execute("""
                SELECT * FROM stock_items 
                WHERE LOWER("ItemCode") LIKE LOWER(?) 
                   OR LOWER("Upc Code") LIKE LOWER(?) 
                   OR LOWER("Description") LIKE LOWER(?) 
                   OR LOWER("Manufacturer Name") LIKE LOWER(?)
            """, (
                '%' + query + '%',
                '%' + query + '%',
                '%' + query + '%',
                '%' + query + '%'
            ))
            results = cursor.fetchall()
            print("Search results:", results)
            conn.close()
    return render_template("index.html", results=results, query=query)

@app.route("/item/<item_code>")
def item_detail(item_code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stock_items WHERE ItemCode = ?", (item_code,))
    item = cursor.fetchone()
    conn.close()

    if item:
        # Build a dictionary for clarity
        item_data = {
            "ItemCode": item[0],
            "UpcCode": item[1],
            "Description": item[2],
            "ManufacturerName": item[3],
            "WarehouseCode": item[4],
            "StockQuantity": item[5]
        }
        print("Item fetched:", item_data)
        return render_template("item_detail.html", item=item_data)
    else:
        return render_template("item_detail.html", item=None), 404

# (Optional) Route to update data manually
@app.route("/update_data", methods=["GET"])
def update_data():
    initialize_db(force_update=True)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
