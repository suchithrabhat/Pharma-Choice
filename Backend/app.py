from flask import Flask, request, jsonify
from flask_cors import CORS
import mysql.connector

app = Flask(__name__)
CORS(app)
# CORS(app, resources={r"/*": {"origins": "*"}})

# =========================
# DB CONNECTION FUNCTION
# =========================
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root123",
        database="pharma_choice"
    )

def get_drug_updated_column(cursor):
    cursor.execute("SHOW COLUMNS FROM drugs")
    columns = [
        column["Field"] if isinstance(column, dict) else column[0]
        for column in cursor.fetchall()
    ]

    return next(
        (column for column in ["updated", "updated_at", "last_updated", "modified_at"] if column in columns),
        None
    )

# =========================
# REGISTER API
# =========================
@app.route('/register', methods=['POST'])
def register():

    try:

        data = request.json

        print("DATA RECEIVED:", data)

        conn = get_db()

        print("DATABASE CONNECTED")

        cursor = conn.cursor()

        sql = """
        INSERT INTO users
        (name,email,phone,gender,age,pincode,password,address)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            data['name'],
            data['email'],
            data['phone'],
            data['gender'],
            int(data['age']),
            data['pincode'],
            data['password'],
            data['address']
        )

        cursor.execute(sql, values)

        print("QUERY EXECUTED")

        conn.commit()

        print("DATA INSERTED")

        cursor.close()
        conn.close()

        return jsonify({
            "message": "Registration Successful"
        })

    except Exception as e:

        print("ERROR:", e)

        return jsonify({
            "message": str(e)
        })


# =========================
# LOGIN API
# =========================
@app.route('/login', methods=['POST'])
def login():

    data = request.json

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    sql = """
    SELECT * FROM users
    WHERE email=%s AND password=%s
    """

    values = (data['email'], data['password'])

    cursor.execute(sql, values)
    user = cursor.fetchone()

    cursor.close()
    conn.close()

    if user:
        return jsonify({"success": True, "user": user})
    else:
        return jsonify({"success": False})


# =========================
# ADD CATEGORY API
# =========================
@app.route('/add_category', methods=['POST'])
def add_category():

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    sql = """
    INSERT INTO categories(category_name)
    VALUES(%s)
    """

    cursor.execute(sql, (data['category'],))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Category Added Successfully"})


# =========================
# VIEW CATEGORY API
# =========================
@app.route('/categories', methods=['GET'])
def categories():

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM categories")
    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)


# =========================
# DELETE CATEGORY API
# =========================
@app.route('/delete_category/<int:id>', methods=['DELETE'])
def delete_category(id):

    conn = get_db()
    cursor = conn.cursor()

    sql = "DELETE FROM categories WHERE id=%s"

    cursor.execute(sql, (id,))
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Category Deleted Successfully"})


# =========================
# ADD DRUG API
# =========================
@app.route('/add_drug', methods=['POST'])
def add_drug():

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    sql = """
    INSERT INTO drugs
    (name,category,price,discount,stock)
    VALUES(%s,%s,%s,%s,%s)
    """

    values = (
        data['name'],
        data['category'],
        data['price'],
        data['discount'],
        data['stock']
    )

    cursor.execute(sql, values)
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"message": "Drug Added Successfully"})


# =========================
# VIEW DRUGS API
# =========================
@app.route('/drugs', methods=['GET'])
def drugs():

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    updated_column = get_drug_updated_column(cursor)

    if updated_column:
        cursor.execute(f"SELECT drugs.*, DATE_FORMAT({updated_column}, '%Y-%m-%d') AS updated FROM drugs")
    else:
        cursor.execute("SELECT * FROM drugs")

    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)


# =========================
# Update DRUGS API
# =========================
@app.route('/update_drug/<int:drug_id>', methods=['PUT'])
def update_drug(drug_id):

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    updated_column = get_drug_updated_column(cursor)
    updated_sql = f", {updated_column}=NOW()" if updated_column else ""

    sql = """
    UPDATE drugs
    SET name=%s,
        category=%s,
        price=%s,
        discount=%s,
        stock=%s
        """ + updated_sql + """
    WHERE id=%s
    """

    values = (
        data['name'],
        data['category'],
        data['price'],
        data['discount'],
        data['stock'],
        drug_id
    )

    cursor.execute(sql, values)
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Drug updated successfully"})



# -------------------------
# Delete Drug (SAVE TO DB)
# -------------------------
@app.route('/delete_drug', methods=['POST'])
def delete_drug():

    data = request.json
    drug_id = data['id']

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM drugs WHERE id = %s", (drug_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Drug deleted successfully"})

# -------------------------
# REDUCE STOCK AFTER ADD TO CART / ORDER
# -------------------------
@app.route('/reduce_stock', methods=['POST'])
def reduce_stock():

    data = request.json

    conn = get_db()
    cursor = conn.cursor()

    updated_column = get_drug_updated_column(cursor)
    updated_sql = f", {updated_column}=NOW()" if updated_column else ""

    cursor.execute("""
        UPDATE drugs
        SET stock = stock - %s
        """ + updated_sql + """
        WHERE id = %s AND stock >= %s
    """, (data['qty'], data['id'], data['qty']))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Stock updated"})


# -------------------------
# PLACE ORDER (SAVE TO DB)
# -------------------------
@app.route('/place_order', methods=['POST'])
def place_order():

    data = request.json
    conn = get_db()
    cursor = conn.cursor()

    sql = """
    INSERT INTO orders
    (username, email, phone, address, drug_name, category, qty, price, total, status, order_date)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    values = (
        data['username'],
        data['email'],
        data['phone'],
        data['address'],
        data['drug_name'],
        data['category'],
        data['qty'],
        data['price'],
        data['total'],
        data['status'],
        data['order_date']
    )

    cursor.execute(sql, values)
    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"success": True})


# -------------------------
# GET ALL ORDERS
# -------------------------
@app.route('/orders', methods=['GET'])
def get_orders():

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM orders
        ORDER BY id DESC
    """)

    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)
  ##User Specific
@app.route('/orders/<email>', methods=['GET'])
def get_user_orders(email):

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM orders
        WHERE email = %s
        ORDER BY id DESC
    """, (email,))

    result = cursor.fetchall()

    cursor.close()
    conn.close()

    return jsonify(result)

# -------------------------
# Update ORDERS
# -------------------------
@app.route('/update_order_status', methods=['POST'])
def update_order_status():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE orders
        SET status = %s
        WHERE id = %s
    """, (data['status'], data['id']))

    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({"success": True})

# -------------------------
# DELETE VIEW ORDERS AFTER DELIVERED
# -------------------------
@app.route('/delete_order', methods=['POST'])
def delete_order():

    data = request.json
    order_id = data.get("id")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM orders WHERE id = %s", (order_id,))

    conn.commit()

    cursor.close()
    conn.close()

    return jsonify({"success": True, "message": "Deleted"})
# =========================
# RUN SERVER
# =========================
if __name__ == '__main__':
    app.run(debug=True, port=5001)
