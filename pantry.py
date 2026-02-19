
def show_pantry():
    try:
        with open("pantry_list.txt", "r") as file:
            print("\n--- YOUR DIGITAL PANTRY ---")
            print(file.read())
    except FileNotFoundError:
        print("\nYour pantry is currently empty.")

def add_item():
    item = input("Enter the ingredient to add: ")
    with open("pantry_list.txt", "a") as file:
        file.write(item + "\n")
    print(f"Added {item} to your pantry!")

print("Welcome to SmartPantry!")
choice = input("Do you want to (V)iew your pantry or (A)dd an item? ").upper()

if choice == "V":
    show_pantry()
elif choice == "A":
    add_item()
else:
    print("Invalid choice! Run the script again.")


