class Student:
    def __init__(self, name, roll_no, marks):
        self.name = name
        self.roll_no = roll_no
        self.marks = marks

    def display_details(self):
        print("Student Details")
        print("----------------")
        print(f"Name     : {self.name}")
        print(f"Roll No  : {self.roll_no}")
        print(f"Marks    : {self.marks}")


# Creating object
student1 = Student("Akshay", 101, 85)
student1.display_details()