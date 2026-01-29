import json

data = {
    "name": "Akshay",
    "role": "Backend Developer",
    "skills": ["Python", "Django"]
}

# Write JSON
with open("users.json", "w") as file:
    json.dump(data, file, indent=4)

print("Data written")

# Read JSON
with open("users.json", "r") as file:
    content = json.load(file)

print("Data read:")
print(content)