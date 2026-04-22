from tkinter import filedialog, messagebox


def OpenFile():
    path = filedialog.askopenfilename(
        title="Open File",
        filetypes=(
            ("PCAP Files", "*.pcapng *.pcap"),
            ("Text Files", "*.txt"),
            ("All Files", "*.*"),
        )
    )
    if not path:
        return
    messagebox.showinfo("Open File", f"Selected:\n{path}")


def SaveFile():
    path = filedialog.asksaveasfilename(
        title="Save File",
        defaultextension=".txt",
        filetypes=(
            ("Text Files", "*.txt"),
            ("PCAP Files", "*.pcapng *.pcap"),
            ("All Files", "*.*"),
        )
    )
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write("")


def Exit(root):
    if messagebox.askyesno("Exit", "Exit application?"):
        root.destroy()
