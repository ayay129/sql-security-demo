import sqlite3
import pytest
from fastapi.testclient import TestClient
from db_security import QueryRejected, query
from main import create_app
from seed import seed


@pytest.fixture
def database(tmp_path):
    path = tmp_path / 'demo.db'
    seed(path)
    return path


def test_select(database):
    result = query(database, 'SELECT id, name FROM products ORDER BY id')
    assert result['rows'] == [[1, 'Keyboard'], [2, 'Mouse']]
    assert result['plan']


def test_aggregate(database):
    assert query(database, 'SELECT count(*) FROM products')['rows'] == [[2]]


@pytest.mark.parametrize('sql', [
    'DELETE FROM products', 'DROP TABLE products',
    "INSERT INTO products VALUES(3, 'x', 1, 1)",
    'UPDATE products SET price=0', 'SELECT * FROM secrets',
    'SELECT internal_cost FROM products', 'SELECT * FROM products',
    'SELECT name FROM sqlite_master', "ATTACH DATABASE ':memory:' AS other",
    'PRAGMA user_version', 'SELECT id FROM products; DELETE FROM products',
    'WITH x AS (SELECT token FROM secrets) SELECT * FROM x',
    'SELECT id FROM products UNION SELECT internal_cost FROM products',
    "SELECT load_extension('x')", '',
])
def test_rejection_preserves_database(database, sql):
    with pytest.raises(QueryRejected):
        query(database, sql)
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT count(*) FROM products').fetchone()[0] == 2


def test_row_limit(database):
    result = query(database, 'SELECT id FROM products', max_rows=1)
    assert len(result['rows']) == 1 and result['truncated']


def test_budget(database):
    with pytest.raises(QueryRejected):
        query(database, 'WITH RECURSIVE x(n) AS (VALUES(1) UNION ALL SELECT n+1 FROM x WHERE n<1000000) SELECT sum(n) FROM x', timeout_seconds=0)


def test_api(database):
    with TestClient(create_app(database)) as client:
        assert client.post('/query', json={'sql': 'SELECT name FROM products'}).status_code == 200
        assert client.post('/query', json={'sql': 'SELECT token FROM secrets'}).status_code == 400
        assert client.post('/query', json={'sql': ''}).status_code == 422
