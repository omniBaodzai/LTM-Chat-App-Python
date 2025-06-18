from tkinter import Tk
# Changed import path to reference the module inside the 'client' package
from client.gui_manager import StartScreen

if __name__ == "__main__":
    root = Tk()
    StartScreen(root)
    root.mainloop()