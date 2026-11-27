import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / "warehouse.sqlite3")
    app.config["TESTING"] = True
    return app.test_client()


def test_create_and_list_multiple_warehouses(client):
    client.post("/warehouses", data={"name": "Food", "capacity": "20"})
    client.post("/warehouses", data={"name": "Tools", "capacity": "50"})

    response = client.get("/")

    assert response.status_code == 200
    assert b"Food" in response.data
    assert b"Tools" in response.data
    assert b"20.0" in response.data


def test_items_can_be_added_and_removed(client):
    client.post("/warehouses", data={"name": "Food", "capacity": "10"})
    warehouse_id = 1
    client.post(
        f"/warehouses/{warehouse_id}/items",
        data={"name": "Apples", "quantity": "6"},
    )
    response = client.get(f"/warehouses/{warehouse_id}")

    assert b"Apples: 6.0" in response.data
    client.post(
        f"/warehouses/{warehouse_id}/items/1/remove",
        data={"quantity": "2"},
    )

    assert b"Apples: 4.0" in client.get(f"/warehouses/{warehouse_id}").data


def test_addition_cannot_exceed_warehouse_capacity(client):
    client.post("/warehouses", data={"name": "Small", "capacity": "5"})
    response = client.post(
        "/warehouses/1/items",
        data={"name": "Heavy item", "quantity": "6"},
        follow_redirects=True,
    )

    assert b"exceeds the warehouse" in response.data
    assert b"Heavy item" not in response.data


def test_items_are_independent_between_warehouses(client):
    client.post("/warehouses", data={"name": "Food", "capacity": "10"})
    client.post("/warehouses", data={"name": "Tools", "capacity": "10"})
    client.post(
        "/warehouses/1/items", data={"name": "Apples", "quantity": "3"}
    )

    assert b"Apples" in client.get("/warehouses/1").data
    assert b"Apples" not in client.get("/warehouses/2").data


def test_warehouse_can_be_updated_and_deleted(client):
    client.post("/warehouses", data={"name": "Old name", "capacity": "10"})
    client.post(
        "/warehouses/1/update",
        data={"name": "New name", "capacity": "15"},
    )

    assert b"New name" in client.get("/").data
    client.post("/warehouses/1/delete")

    assert b"New name" not in client.get("/").data
    assert client.get("/warehouses/1").status_code == 404


def test_capacity_cannot_be_reduced_below_stored_quantity(client):
    client.post("/warehouses", data={"name": "Food", "capacity": "10"})
    client.post("/warehouses/1/items", data={"name": "Apples", "quantity": "8"})
    response = client.post(
        "/warehouses/1/update",
        data={"name": "Food", "capacity": "5"},
        follow_redirects=True,
    )

    assert b"Capacity cannot be less" in response.data
    assert b"8.0 / 10.0" in response.data
