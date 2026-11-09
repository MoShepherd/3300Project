from flask import Flask, render_template_string, request, redirect, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = "landlord-management-secret"


# ---------------------------------------------------------
# Database configuration
# ---------------------------------------------------------

DB_CONFIG = {
    "host": "mysql",
    "port": 3306,  # Internal Docker port, NOT 3307
    "user": "user",
    "password": "password",
    "database": "landlorddb"
}


def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


# ---------------------------------------------------------
# Database initialization
# ---------------------------------------------------------

def initialize_database():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tenants (
                tenant_id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL
            )
        """)
        connection.commit()
    finally:
        cursor.close()
        connection.close()


# ---------------------------------------------------------
# HTML template
# ---------------------------------------------------------

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Landlord Management</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f6f9;
            margin: 0;
            padding: 40px;
        }

        .container {
            max-width: 800px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.08);
        }

        h1 {
            margin-top: 0;
            margin-bottom: 25px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }

        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }

        th {
            background-color: #f0f2f5;
        }

        .actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        input {
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            flex: 1;
        }

        button {
            padding: 10px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }

        .add-button {
            background-color: #2563eb;
            color: white;
        }

        .remove-button {
            background-color: #dc2626;
            color: white;
        }

        .refresh-button {
            background-color: #64748b;
            color: white;
        }

        .message {
            padding: 10px;
            margin-bottom: 15px;
            border-radius: 5px;
            background-color: #e0f2fe;
        }

        .empty {
            color: #777;
            text-align: center;
            padding: 20px;
        }
    </style>
</head>

<body>
    <div class="container">

        <h1>Landlord Management</h1>

        {% with messages = get_flashed_messages() %}
            {% for message in messages %}
                <div class="message">{{ message }}</div>
            {% endfor %}
        {% endwith %}

        <h2>Tenants</h2>

        <table>
            <thead>
                <tr>
                    <th>Tenant ID</th>
                    <th>Tenant Name</th>
                    <th>Action</th>
                </tr>
            </thead>

            <tbody>
                {% for tenant in tenants %}
                    <tr>
                        <td>{{ tenant[0] }}</td>
                        <td>{{ tenant[1] }}</td>
                        <td>
                            <form method="POST"
                                  action="{{ url_for('remove_tenant', tenant_id=tenant[0]) }}"
                                  onsubmit="return confirm('Do you really want to remove {{ tenant[1] }}?');">
                                <button class="remove-button" type="submit">
                                    Remove
                                </button>
                            </form>
                        </td>
                    </tr>
                {% else %}
                    <tr>
                        <td colspan="3" class="empty">
                            No tenants found.
                        </td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>

        <h2>Add Tenant</h2>

        <form method="POST" action="{{ url_for('add_tenant') }}" class="actions">
            <input
                type="text"
                name="name"
                placeholder="Enter tenant name"
                maxlength="100"
                required
            >

            <button class="add-button" type="submit">
                + Add Tenant
            </button>
        </form>

        <div class="actions">
            <form method="GET" action="{{ url_for('index') }}">
                <button class="refresh-button" type="submit">
                    Refresh
                </button>
            </form>
        </div>

    </div>
</body>
</html>
"""


# ---------------------------------------------------------
# Routes
# ---------------------------------------------------------

@app.route("/")
def index():
    tenants = []

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT tenant_id, name FROM tenants ORDER BY tenant_id"
        )

        tenants = cursor.fetchall()

        cursor.close()
        connection.close()

    except mysql.connector.Error as error:
        flash(f"Database error: {error}")

    return render_template_string(HTML_TEMPLATE, tenants=tenants)


@app.route("/add", methods=["POST"])
def add_tenant():
    name = request.form.get("name", "").strip()

    if not name:
        flash("Tenant name cannot be empty.")
        return redirect(url_for("index"))

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO tenants (name) VALUES (%s)",
            (name,)
        )

        connection.commit()

        cursor.close()
        connection.close()

        flash(f"Tenant '{name}' added successfully.")

    except mysql.connector.Error as error:
        flash(f"Database error: {error}")

    return redirect(url_for("index"))


@app.route("/remove/<int:tenant_id>", methods=["POST"])
def remove_tenant(tenant_id):
    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM tenants WHERE tenant_id = %s",
            (tenant_id,)
        )

        connection.commit()

        if cursor.rowcount > 0:
            flash("Tenant removed successfully.")
        else:
            flash("Tenant not found.")

        cursor.close()
        connection.close()

    except mysql.connector.Error as error:
        flash(f"Database error: {error}")

    return redirect(url_for("index"))


# ---------------------------------------------------------
# Start application
# ---------------------------------------------------------

if __name__ == "__main__":
    initialize_database()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )