import math
import os

from flask import Flask, flash, redirect, render_template, request, url_for

import database


def create_app(database_path=None):  # pylint: disable=too-many-statements
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or os.urandom(32)
    app.config["DATABASE"] = database_path or os.environ.get(
        "WAREHOUSE_DATABASE",
        os.path.join(app.instance_path, "warehouse.sqlite3"),
    )

    database.initialize_database(app.config["DATABASE"])

    @app.get("/")
    def index():
        warehouses = database.list_warehouses(app.config["DATABASE"])
        return render_template("index.html", warehouses=warehouses)

    @app.post("/warehouses")
    def create_warehouse():
        name = request.form.get("name", "").strip()
        capacity = _positive_number(request.form.get("capacity"))
        if not name or capacity is None:
            flash("Enter a warehouse name and a positive capacity.")
            return redirect(url_for("index"))
        database.create_warehouse(app.config["DATABASE"], name, capacity)
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

        result = database.update_warehouse(
            app.config["DATABASE"], warehouse_id, name, capacity
        )
        if result == "not_found":
            return "Warehouse not found", 404
        if result == "capacity":
            flash("Capacity cannot be less than the quantity already stored.")
            return redirect(
                url_for("warehouse_detail", warehouse_id=warehouse_id)
            )
        flash("Warehouse updated.")
        return redirect(
            url_for("warehouse_detail", warehouse_id=warehouse_id)
        )

    @app.post("/warehouses/<int:warehouse_id>/delete")
    def delete_warehouse(warehouse_id):
        if not database.delete_warehouse(app.config["DATABASE"], warehouse_id):
            return "Warehouse not found", 404
        flash("Warehouse deleted.")
        return redirect(url_for("index"))

    @app.get("/warehouses/<int:warehouse_id>")
    def warehouse_detail(warehouse_id):
        details = database.get_warehouse(app.config["DATABASE"], warehouse_id)
        if details is None:
            return "Warehouse not found", 404
        warehouse, items, used = details
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

        result = database.add_item(
            app.config["DATABASE"], warehouse_id, name, quantity
        )
        if result == "not_found":
            return "Warehouse not found", 404
        if result == "capacity":
            flash("That quantity exceeds the warehouse's available capacity.")
            return redirect(
                url_for("warehouse_detail", warehouse_id=warehouse_id)
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
        result = database.remove_item(
            app.config["DATABASE"], warehouse_id, item_id, quantity
        )
        if result == "not_found":
            return "Item not found", 404
        if result == "insufficient":
            flash("There is not enough of that item in the warehouse.")
            return redirect(
                url_for("warehouse_detail", warehouse_id=warehouse_id)
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
