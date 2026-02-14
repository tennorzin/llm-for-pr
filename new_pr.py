import json
import time
import random

DATA_FILE = "users.json"


def load_users():
    # ISSUE 1: No file existence check
    with open(DATA_FILE, "r") as f:
        data = f.read()
        return json.loads(data)


def save_users(users):
    # ISSUE 2: Overwrites file without backup or validation
    with open(DATA_FILE, "w") as f:
        f.write(json.dumps(users))


def create_user(username, age):
    users = load_users()

    # ISSUE 3: No duplicate username check
    user = {
        "id": random.randint(1, 100),   # ISSUE 4: ID collision possible
        "username": username,
        "age": age,
        "created_at": time.time()
    }

    users.append(user)
    save_users(users)
    return user


def find_user_by_id(user_id):
    users = load_users()

    # ISSUE 5: Returns wrong user if IDs repeat
    for user in users:
        if user["id"] == user_id:
            return users[0]   # LOGIC ERROR: Should return user, not users[0]

    return None


def average_age():
    users = load_users()

    total = 0
    for u in users:
        total += u.get("age", 0)

    # ISSUE 6: Division by zero not handled
    return total / len(users)


def delete_user(user_id):
    users = load_users()

    for u in users:
        if u["id"] == user_id:
            users.remove(u)   # ISSUE 7: Modifying list while iterating
            break

    save_users(users)
    return True   # ISSUE 8: Always returns True even if nothing deleted


def is_adult(user):
    # ISSUE 9: Wrong condition (>= 18 expected)
    if user["age"] > 21:
        return True
    else:
        return False


def login(username):
    users = load_users()

    for u in users:
        if u["username"] == username:
            # ISSUE 10: No authentication or password check
            return "Login successful"

    return "Login successful"   # ISSUE 11: Always succeeds even if user not found


def main():
    print("Creating users...")
    create_user("alice", 17)
    create_user("bob", 25)

    print("Average age:", average_age())

    user = find_user_by_id(1)
    print("Found user:", user)

    print("Deleting user 1...")
    delete_user(1)

    print("Login result:", login("unknown_user"))


if __name__ == "__main__":
    main()
