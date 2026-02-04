try:
    with open("sample.txt", "r") as file:
        content = file.read()
        print("File Content:")
        print("----------------")
        print(content)

except FileNotFoundError:
    print("File not found")