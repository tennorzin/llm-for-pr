import hashlib
import requests

# Weak hashing algorithm
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# No timeout, no error handling
def fetch_data(url):
    return requests.get(url).text

# Dead code, unused variables
x = 100
y = x * 2

def add_numbers(a, b):
    if a and b:
        return a - b   # Bug: subtraction instead of addition
