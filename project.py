from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    abort
)

from werkzeug.security import check_password_hash
from functools import wraps
import mysql.connector
from mysql.connector import Error

app = Flask(__name__)
app.secret_key = "landlord-management-secret"
# Update these settings for your MySQL installation.
DB_CONFIG = {
    "host": "mysql",
    "port": 3306,  # Internal Docker port, NOT 3307
    "user": "user",
    "password": "password",
    "database": "landlorddb"
}

# Table and column names are deliberately defined here (whitelisted).
# The boolean-like VARCHAR columns are stored as "Yes" / "No".
TABLES = {
    "Houses": {
        "primary_key": "Address",
        "fields": [
            ("Address", "text", True),
            ("Apartment_count", "number", False),
            ("Property_value", "number", False),
        ],
        "booleans": [],
    },
    "Apartments": {
        "primary_key": "Apartment_ID",
        "fields": [
            ("Apartment_ID", "number", True),
            ("address", "text", False),
            ("number", "number", False),
            ("size", "number", False),
            ("room_count", "number", False),
            ("has_parking_lot", "boolean", False),
        ],
        "booleans": ["has_parking_lot"],
    },
    "Tennents": {
        "primary_key": "Tennent_ID",
        "fields": [
            ("Tennent_ID", "number", True),
            ("surname", "text", False),
            ("name", "text", False),
            ("warning_count", "number", False),
        ],
        "booleans": [],
    },
    "Contractors": {
        "primary_key": "Contract_ID",
        "fields": [
            ("Contract_ID", "number", True),
            ("con_surname", "text", False),
            ("con_name", "text", False),
            ("address", "text", False),
            ("profession", "text", False),
        ],
        "booleans": [],
    },
    "Leases": {
        "primary_key": "Lease_ID",
        "fields": [
            ("Lease_ID", "number", True),
            ("Apartment_ID", "number", False),
            ("tennent_ID", "number", False),
            ("Validation_date", "date", False),
            ("rent", "number", False),
            ("utilities", "number", False),
            ("termination", "date", False),
        ],
        "booleans": [],
    },
    "Warnings": {
        "primary_key": "Warning_ID",
        "fields": [
            ("Warning_ID", "number", True),
            ("lease_ID", "number", False),
            ("date", "date", False),
            ("fine_amount", "number", False),
            ("is_paid", "boolean", False),
        ],
        "booleans": ["is_paid"],
    },
    "Repairs": {
        "primary_key": "repair_ID",
        "fields": [
            ("repair_ID", "number", True),
            ("apartment_ID", "number", False),
            ("Contract_ID", "number", False),
            ("issue_description", "text", False),
            ("repair_cost", "number", False),
            ("completion_status", "boolean", False),
        ],
        "booleans": ["completion_status"],
    },
}

#Function for Query 1:
def get_total_property_value():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("CALL get_total_value()")

        row = cursor.fetchone()
        return row["total"] 

    finally:
        cursor.close()
        connection.close()

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)


def get_table_or_404(table_name):
    if table_name not in TABLES:
        abort(404)
    return TABLES[table_name]


def quote_identifier(identifier):
    # Only identifiers from the TABLES whitelist are passed here.
    return "`" + identifier.replace("`", "``") + "`"

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:
            return redirect(url_for("login"))

        return f(*args, **kwargs)

    return decorated_function


@app.route("/")
@login_required
def dashboard():
    return render_template("dashboard.html", tables=TABLES)

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT User_ID, username, password_hash, role
            FROM Users
            WHERE username = %s
        """, (username,))

        user = cursor.fetchone()

        cursor.close()
        connection.close()

        if user and user["password_hash"] == password:
            session.clear()

            session["user_id"] = user["User_ID"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")

@app.route("/table/<table_name>")
@login_required
def show_table(table_name):
    config = get_table_or_404(table_name)
    columns = [field[0] for field in config["fields"]]
    search = request.args.get("q", "").strip()

    sql = "SELECT " + ", ".join(quote_identifier(c) for c in columns)
    sql += " FROM " + quote_identifier(table_name)
    params = []

    if search:
        conditions = [
            "CAST(" + quote_identifier(c) + " AS CHAR) LIKE %s"
            for c in columns
        ]
        sql += " WHERE " + " OR ".join(conditions)
        params = [f"%{search}%"] * len(columns)

    sql += " ORDER BY " + quote_identifier(config["primary_key"])

    connection = get_connection()
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql, params)
        rows = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    
    property_value = None

    if table_name == "Houses":
        property_value = get_total_property_value()

    return render_template(
        "relation.html",
        table_name=table_name,
        config=config,
        columns=columns,
        rows=rows,
        search=search,
        property_value=property_value
    )


@app.route("/table/<table_name>/add", methods=["POST"])
@login_required
def add_record(table_name):
    config = get_table_or_404(table_name)
    fields = config["fields"]
    columns = []
    values = []

    try:
        for column, field_type, is_primary_key in fields:
            if field_type == "boolean":
                value = "Yes" if request.form.get(column) == "on" else "No"
            else:
                value = request.form.get(column, "").strip()
                if value == "":
                    value = None

            if is_primary_key and value is None:
                raise ValueError(f"{column} is required.")

            columns.append(column)
            values.append(value)

        sql = (
            "INSERT INTO " + quote_identifier(table_name)
            + " (" + ", ".join(quote_identifier(c) for c in columns) + ")"
            + " VALUES (" + ", ".join(["%s"] * len(values)) + ")"
        )

        connection = get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(sql, values)
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        flash("Record added successfully.", "success")

    except ValueError as exc:
        flash(str(exc), "error")
    except Error as exc:
        flash(f"Could not add record: {exc}", "error")

    return redirect(url_for("show_table", table_name=table_name))


@app.route("/table/<table_name>/delete", methods=["POST"])
@login_required
def delete_records(table_name):
    config = get_table_or_404(table_name)
    primary_key = config["primary_key"]
    selected_ids = request.form.getlist("selected_ids")

    if not selected_ids:
        flash("Select at least one record to delete.", "error")
        return redirect(url_for("show_table", table_name=table_name))

    placeholders = ", ".join(["%s"] * len(selected_ids))
    sql = (
        "DELETE FROM " + quote_identifier(table_name)
        + " WHERE " + quote_identifier(primary_key)
        + " IN (" + placeholders + ")"
    )

    try:
        connection = get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute(sql, selected_ids)
            deleted_count = cursor.rowcount
            connection.commit()
        finally:
            cursor.close()
            connection.close()

        flash(f"Deleted {deleted_count} record(s).", "success")
    except Error as exc:
        flash(f"Could not delete record(s): {exc}", "error")

    return redirect(url_for("show_table", table_name=table_name))

@app.route("/table/houses/check", methods=["POST"])
@login_required
def check_invest():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL get_critical_houses",
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve investment check: {exc}", "error")
        return redirect(url_for("show_table", table_name="Houses"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route("/table/houses/earnings", methods=["POST"])
@login_required
def check_house():

    address = request.form.get("address")

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL check_house(%s)",
            (address,) 
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve earnings: {exc}", "error")
        return redirect(url_for("show_table", table_name="Houses"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route("/table/tennents/warninginfo", methods=["POST"])
@login_required
def new_warning():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL new_warning_letter"
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve warning infos: {exc}", "error")
        return redirect(url_for("show_table", table_name="Tennents"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route("/table/apartments/free", methods=["POST"])
@login_required
def free_apartments():
    size = request.form.get("size")
    rooms = request.form.get("rooms")
    parking = "Yes" if request.form.get("parking") == "on" else "No"

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL get_apartments(%s, %s, %s)",
            (size, rooms, parking)
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve free apartments: {exc}", "error")
        return redirect(url_for("show_table", table_name="Apartments"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route("/table/apartments/broken", methods=["POST"])
@login_required
def broken_apartments():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL show_broken_apartments",
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve broken apartments: {exc}", "error")
        return redirect(url_for("show_table", table_name="Apartments"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route("/table/leases/critical-leases", methods=["POST"])
@login_required
def critical_leases():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL get_critical_lease",
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve critical leases: {exc}", "error")
        return redirect(url_for("show_table", table_name="Leases"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route("/table/contractors/lessjobs", methods=["POST"])
@login_required
def less_jobs():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL get_less_jobs",
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve contractors with less jobs: {exc}", "error")
        return redirect(url_for("show_table", table_name="Contractors"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

@app.route("/table/repairs/prioritize", methods=["POST"])
@login_required
def prio_repairs():

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "CALL prio_repairs",
        )

        rows = cursor.fetchall()
        columns = cursor.column_names

        return render_template(
            "relation.html",
            rows=rows,
            columns=columns
        )

    except Error as exc:
        flash(f"Could not retrieve prioritize repairs: {exc}", "error")
        return redirect(url_for("show_table", table_name="Repairs"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)