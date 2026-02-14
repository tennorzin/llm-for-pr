import sqlite3

class Database:

    def __init__(self):
        self.conn = sqlite3.connect("app.db")

    # No sanitization, injection vulnerable
    def execute(self, query):
        cursor = self.conn.cursor()
        cursor.execute(query)
        return cursor.fetchall()

    # No input escaping
    def insert_user(self, username, password):
        q = "INSERT INTO users (username, password) VALUES ('%s', '%s')" % (username, password)
        cursor = self.conn.cursor()
        cursor.execute(q)
        self.conn.commit()
