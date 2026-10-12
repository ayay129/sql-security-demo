import sqlite3
from pathlib import Path


def seed(path):
    with sqlite3.connect(path) as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY, name TEXT, price REAL, internal_cost REAL);
        CREATE TABLE IF NOT EXISTS secrets(token TEXT);
        DELETE FROM products;
        DELETE FROM secrets;
        INSERT INTO products VALUES(1, 'Keyboard', 199, 80), (2, 'Mouse', 99, 30);
        INSERT INTO secrets VALUES('demo-only-token');
        ''')


if __name__ == '__main__':
    seed(Path(__file__).with_name('demo.db'))
    print('Created demo.db with synthetic data')
