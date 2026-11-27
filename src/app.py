import math
import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, url_for


def create_app(database_path=None):  # pylint: disable=too-many-statements
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(32)
    app.config["DATABASE"] = database_path or os.environ.get(
        "WAREHOUSE_DATABASE",
        os.path.join(app.instance_path, "warehouse.sqlite3"),
    )

    os.makedirs(
        os.path.dirname(os.path.abspath(app.config["DATABASE"])), exist_ok=True
    )

    with sqlite3.connect(app.config["DATABASE"]) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS warehouses (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                capacity REAL NOT NULL CHECK (capacity > 0)
            );
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                warehouse_id INTEGER NOT NULL
                    REFERENCES warehouses(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                quantity REAL NOT NULL CHECK (quantity >= 0),
                UNIQUE (warehouse_id, name)
            );
            """
        )

    def connect_db():
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @app.get("/")
    def index():
        with connect_db() as connection:
            warehouses = connection.execute(
                """
                SELECT warehouses.id, warehouses.name, warehouses.capacity,
                       COALESCE(SUM(items.quantity), 0) AS used
                FROM warehouses LEFT JOIN items
                    ON items.warehouse_id = warehouses.id
                GROUP BY warehouses.id ORDER BY warehouses.id
                """
            ).fetchall()
        return render_template("index.html", warehouses=warehouses)

    @app.post("/warehouses")
    def create_warehouse():
        name = request.form.get("name", "").strip()
        capacity = _positive_number(request.form.get("capacity"))
        if not name or capacity is None:
            flash("Enter a warehouse name and a positive capacity.")
            return redirect(url_for("index"))
        with connect_db() as connection:
            connection.execute(
                "INSERT INTO warehouses (name, capacity) VALUES (?, ?)",
                (name, capacity),
            )
        flash("Warehouse created.")
        return redirect(url_for("index"))

    @app.post("/warehouses/<int:warehouse_id>/update")
    def update_warehouse(warehouse_id):  # pylint: disable=too-many-statements
        name = request.form.get("name", "").strip()
        capacity = _positive_number(request.form.get("capacity"))
        if not name or capacity is None:
            flash("Enter a warehouse name and a positive capacity.")
            return redirect(
                url_for("warehouse_detail", warehouse_id=warehouse_id)
            )

        with connect_db() as connection:
            warehouse = connection.execute(
                """
                SELECT capacity, COALESCE(
                    (SELECT SUM(quantity) FROM items WHERE warehouse_id = ?), 0
                ) AS used
                FROM warehouses WHERE id = ?
                """,
                (warehouse_id, warehouse_id),
            ).fetchone()
            if warehouse is None:
                return "Warehouse not found", 404
            if capacity < warehouse["used"]:
                flash(
                    "Capacity cannot be less than the quantity already stored."
                )
                return redirect(
                    url_for("warehouse_detail", warehouse_id=warehouse_id)
                )
            connection.execute(
                "UPDATE warehouses SET name = ?, capacity = ? WHERE id = ?",
                (name, capacity, warehouse_id),
            )
        flash("Warehouse updated.")
        return redirect(
            url_for("warehouse_detail", warehouse_id=warehouse_id)
        )

    @app.post("/warehouses/<int:warehouse_id>/delete")
    def delete_warehouse(warehouse_id):
        with connect_db() as connection:
            cursor = connection.execute(
                "DELETE FROM warehouses WHERE id = ?", (warehouse_id,)
            )
            if cursor.rowcount == 0:
                return "Warehouse not found", 404
        flash("Warehouse deleted.")
        return redirect(url_for("index"))

    @app.get("/warehouses/<int:warehouse_id>")
    def warehouse_detail(warehouse_id):
        with connect_db() as connection:
            warehouse = connection.execute(
                "SELECT * FROM warehouses WHERE id = ?", (warehouse_id,)
            ).fetchone()
            if warehouse is None:
                return "Warehouse not found", 404
            items = connection.execute(
                "SELECT * FROM items WHERE warehouse_id = ? ORDER BY name",
                (warehouse_id,),
            ).fetchall()
            used = sum(item["quantity"] for item in items)
        return render_template(
            "warehouse.html", warehouse=warehouse, items=items, used=used
        )

    @app.post("/warehouses/<int:warehouse_id>/items")
    def add_item(warehouse_id):  # pylint: disable=too-many-statements
        name = request.form.get("name", "").strip()
        quantity = _positive_number(request.form.get("quantity"))
        if not name or quantity is None:
            flash("Enter an item name and a positive quantity.")
            return redirect(
                url_for("warehouse_detail", warehouse_id=warehouse_id)
            )

        with connect_db() as connection:
            connection.execute("BEGIN IMMEDIATE")
            warehouse = connection.execute(
                "SELECT capacity FROM warehouses WHERE id = ?", (warehouse_id,)
            ).fetchone()
            if warehouse is None:
                return "Warehouse not found", 404
            used = connection.execute(
                "SELECT COALESCE(SUM(quantity), 0) FROM items "
                "WHERE warehouse_id = ?",
                (warehouse_id,),
            ).fetchone()[0]
            if quantity > warehouse["capacity"] - used:
                flash(
                    "That quantity exceeds the warehouse's available capacity."
                )
                return redirect(
                    url_for("warehouse_detail", warehouse_id=warehouse_id)
                )
            connection.execute(
                """
                INSERT INTO items (warehouse_id, name, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT (warehouse_id, name)
                DO UPDATE SET quantity = quantity + excluded.quantity
                """,
                (warehouse_id, name, quantity),
            )
        flash("Item added.")
        return redirect(url_for("warehouse_detail", warehouse_id=warehouse_id))

    @app.post("/warehouses/<int:warehouse_id>/items/<int:item_id>/remove")
    # pylint: disable=too-many-statements
    def remove_item(warehouse_id, item_id):
        quantity = _positive_number(request.form.get("quantity"))
        if quantity is None:
            flash("Enter a positive quantity.")
            return redirect(
                url_for("warehouse_detail", warehouse_id=warehouse_id)
            )
        with connect_db() as connection:
            item = connection.execute(
                "SELECT quantity FROM items WHERE id = ? AND warehouse_id = ?",
                (item_id, warehouse_id),
            ).fetchone()
            if item is None:
                return "Item not found", 404
            if quantity > item["quantity"]:
                flash("There is not enough of that item in the warehouse.")
                return redirect(
                    url_for("warehouse_detail", warehouse_id=warehouse_id)
                )
            if quantity == item["quantity"]:
                connection.execute("DELETE FROM items WHERE id = ?", (item_id,))
            else:
                connection.execute(
                    "UPDATE items SET quantity = quantity - ? WHERE id = ?",
                    (quantity, item_id),
                )
        flash("Item removed.")
        return redirect(url_for("warehouse_detail", warehouse_id=warehouse_id))

    return app


def _positive_number(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number <= 0 or not math.isfinite(number):
        return None
    return number


application = create_app()


if __name__ == "__main__":
    application.run(debug=os.environ.get("FLASK_DEBUG") == "1")
