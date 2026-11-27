import os
import sqlite3
from contextlib import contextmanager


@contextmanager
def _connect(database_path):  # pylint: disable=too-many-statements
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def initialize_database(database_path):
    os.makedirs(os.path.dirname(os.path.abspath(database_path)), exist_ok=True)
    with _connect(database_path) as connection:
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


def list_warehouses(database_path):
    with _connect(database_path) as connection:
        return connection.execute(
            """
            SELECT warehouses.id, warehouses.name, warehouses.capacity,
                   COALESCE(SUM(items.quantity), 0) AS used
            FROM warehouses LEFT JOIN items
                ON items.warehouse_id = warehouses.id
            GROUP BY warehouses.id ORDER BY warehouses.id
            """
        ).fetchall()


def create_warehouse(database_path, name, capacity):
    with _connect(database_path) as connection:
        connection.execute(
            "INSERT INTO warehouses (name, capacity) VALUES (?, ?)",
            (name, capacity),
        )


def update_warehouse(database_path, warehouse_id, name, capacity):
    with _connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        warehouse = connection.execute(
            """
            SELECT COALESCE(
                (SELECT SUM(quantity) FROM items WHERE warehouse_id = ?), 0
            ) AS used
            FROM warehouses WHERE id = ?
            """,
            (warehouse_id, warehouse_id),
        ).fetchone()
        if warehouse is None:
            return "not_found"
        if capacity < warehouse["used"]:
            return "capacity"
        connection.execute(
            "UPDATE warehouses SET name = ?, capacity = ? WHERE id = ?",
            (name, capacity, warehouse_id),
        )
    return "updated"


def delete_warehouse(database_path, warehouse_id):
    with _connect(database_path) as connection:
        cursor = connection.execute(
            "DELETE FROM warehouses WHERE id = ?", (warehouse_id,)
        )
        return cursor.rowcount > 0


def get_warehouse(database_path, warehouse_id):
    with _connect(database_path) as connection:
        warehouse = connection.execute(
            "SELECT * FROM warehouses WHERE id = ?", (warehouse_id,)
        ).fetchone()
        if warehouse is None:
            return None
        items = connection.execute(
            "SELECT * FROM items WHERE warehouse_id = ? ORDER BY name",
            (warehouse_id,),
        ).fetchall()
    used = sum(item["quantity"] for item in items)
    return warehouse, items, used


def add_item(database_path, warehouse_id, name, quantity):
    with _connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        warehouse = connection.execute(
            "SELECT capacity FROM warehouses WHERE id = ?", (warehouse_id,)
        ).fetchone()
        if warehouse is None:
            return "not_found"
        used = connection.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM items "
            "WHERE warehouse_id = ?",
            (warehouse_id,),
        ).fetchone()[0]
        if quantity > warehouse["capacity"] - used:
            return "capacity"
        connection.execute(
            """
            INSERT INTO items (warehouse_id, name, quantity)
            VALUES (?, ?, ?)
            ON CONFLICT (warehouse_id, name)
            DO UPDATE SET quantity = quantity + excluded.quantity
            """,
            (warehouse_id, name, quantity),
        )
    return "added"


def remove_item(database_path, warehouse_id, item_id, quantity):
    with _connect(database_path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        item = connection.execute(
            "SELECT quantity FROM items WHERE id = ? AND warehouse_id = ?",
            (item_id, warehouse_id),
        ).fetchone()
        if item is None:
            return "not_found"
        if quantity > item["quantity"]:
            return "insufficient"
        if quantity == item["quantity"]:
            connection.execute("DELETE FROM items WHERE id = ?", (item_id,))
        else:
            connection.execute(
                "UPDATE items SET quantity = quantity - ? WHERE id = ?",
                (quantity, item_id),
            )
    return "removed"
