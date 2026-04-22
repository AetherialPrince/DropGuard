#============= IMPORTS ===============#
import os, sys
from tkinter import filedialog

#============== UTILS ================#

# returns correct path nomatter if script of exe

def resource_path(relative):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.abspath("."), relative)
