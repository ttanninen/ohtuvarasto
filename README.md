# ohtuvarasto

[![GHA workflow badge](https://github.com/ttanninen/ohtuvarasto/actions/workflows/main.yml/badge.svg)](https://github.com/ttanninen/ohtuvarasto/actions)

[![codecov](https://codecov.io/github/ttanninen/ohtuvarasto/graph/badge.svg?token=7KSQA4X58E)](https://codecov.io/github/ttanninen/ohtuvarasto)

## Web application

Install the project dependencies and start the Flask app:

```sh
uv sync
uv run python src/app.py
```

Open http://127.0.0.1:5000 to create and view warehouses. Each warehouse has a
capacity and its own list of items; adding stock cannot exceed the capacity,
and items can be removed from their warehouse. SQLite data is stored in
`src/instance/warehouse.sqlite3` by default. Set `WAREHOUSE_DATABASE` to use a
different database path.
