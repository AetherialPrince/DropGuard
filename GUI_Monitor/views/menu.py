
from tkinter import Menu
from .MenuHelpers import SaveFile, OpenFile, Exit


class AppMenu:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.build()

    def build(self):
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        filemenu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=filemenu)
        filemenu.add_command(label="Open…", command=OpenFile)
        filemenu.add_command(label="Save As…", command=SaveFile)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=lambda: Exit(self.root))
