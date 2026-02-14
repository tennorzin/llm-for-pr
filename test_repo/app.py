import os
import utils
from database import Database
from config import SECRET_KEY

# Hardcoded API key (bad)
API_KEY = "12345-ABCDE"

# SQL injection vulnerability
def get_user(username):
    db = Database()
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return db.execute(query)

# Dangerous: exposing secret key
print("Loaded Secret:", SECRET_KEY)

def main():
    username = input("Enter username: ")
    user = get_user(username)  # No validation
    print("Fetched user:", user)

    # Unsafe eval usage
    print(eval(input("Enter something to eval: ")))

if __name__ == "__main__":
    main()
