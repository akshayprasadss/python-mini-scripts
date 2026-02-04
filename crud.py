users = []

def create_user(id, name):
    users.append({"id": id, "name": name})
    print("User created")

def read_users():
    print("Users:")
    for user in users:
        print(user)

def update_user(id, name):
    for user in users:
        if user["id"] == id:
            user["name"] = name
            print("User updated")
            return
    print("User not found")

def delete_user(id):
    for user in users:
        if user["id"] == id:
            users.remove(user)
            print("User deleted")
            return
    print("User not found")

# Test
create_user(1, "Akshay")
create_user(2, "Rahul")
read_users()
update_user(1, "Akshay Prasad")
delete_user(2)
read_users()