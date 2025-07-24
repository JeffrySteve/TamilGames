# Entry point with webcam + menu

import cv2
from game_logic import game_drag_drop, game_finger_count
def show_menu():
    print("\n===== Tamil Kids Learning Games =====")
    print("1) Drag-Drop Matching")
    print("2) Finger Counting")
    print("3) Air Tracing Tamil Letters")
    print("4) Exit")

def main():
    while True:
        show_menu()
        choice = input("Select a game (1-4): ")

        if choice == '1':
            game_drag_drop()
        elif choice == '2':
            game_finger_count()
        elif choice == '4':
            print("Exiting Tamil Kids Learning Games. Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1-4.")

if __name__ == "__main__":
    main()