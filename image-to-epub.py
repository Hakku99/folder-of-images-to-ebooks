import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Listbox, END, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from PIL import Image
from ebooklib import epub
from io import BytesIO
import zipfile
import threading

# --- UI Theme ---
class Style:
    BG = '#2b2b2b'
    FG = '#dcdcdc'
    LIST_BG = '#3c3f41'
    PLACEHOLDER_FG = '#6e7072'
    BTN_BG = '#007acc'
    BTN_HOVER = '#005f9e'
    SUCCESS = '#4caf50'
    ERROR = '#f44336'
    FONT = ("Segoe UI", 10)
    FONT_TITLE = ("Segoe UI", 14, "bold")
    FONT_MONO = ("Consolas", 9)

# --- Image Processing ---
def process_image(path):
    try:
        with Image.open(path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            buffer = BytesIO()
            img.save(buffer, format='JPEG', quality=100, subsampling=0)
            return buffer.getvalue()
    except Exception:
        return None

# --- EPUB Creation ---
def create_epub(folder, out_dir, logger, progress, stop_flag):
    name = os.path.basename(folder)
    logger(f"[EPUB] Processing {name}")
    book = epub.EpubBook()
    book.set_identifier(name)
    book.set_title(name)
    book.set_language('en')
    book.add_author('AutoGen')
    pages = []

    files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('jpg','jpeg','png','gif','bmp','webp'))])
    for idx, img in enumerate(files):
        if stop_flag(): return
        p = os.path.join(folder, img)
        data = process_image(p)
        if not data: continue

        img_name = f'image_{idx:03d}.jpg'
        item = epub.EpubItem(uid=f'img_{idx}', file_name=f'images/{img_name}', media_type='image/jpeg', content=data)
        book.add_item(item)

        html = f'<html><body><img src="images/{img_name}" style="max-width:100%;max-height:100%;display:block;margin:auto;background:black;"/></body></html>'
        page = epub.EpubHtml(title=f'Page {idx+1}', file_name=f'page_{idx+1}.xhtml', content=html)
        book.add_item(page)
        pages.append(page)
        progress(1)

    book.spine = pages
    book.toc = tuple(pages)
    book.add_item(epub.EpubNav())
    book.add_item(epub.EpubNcx())

    out_path = os.path.join(out_dir, f"{name}.epub")
    epub.write_epub(out_path, book)
    logger(f"✓ Saved: {out_path}")

# --- CBZ Creation ---
def create_cbz(folder, out_dir, logger, progress, stop_flag):
    name = os.path.basename(folder)
    logger(f"[CBZ] Processing {name}")
    out_path = os.path.join(out_dir, f"{name}.cbz")
    files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('jpg','jpeg','png','gif','bmp','webp'))])

    with zipfile.ZipFile(out_path, 'w') as cbz:
        for idx, f in enumerate(files):
            if stop_flag(): return
            path = os.path.join(folder, f)
            data = process_image(path)
            if not data: continue
            img_name = f'{idx:03d}.jpg'
            cbz.writestr(img_name, data)
            progress(1)
    logger(f"✓ Saved: {out_path}")

# --- Main App ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to EPUB/CBZ Converter")
        self.root.geometry("800x600")
        self.root.configure(bg=Style.BG)

        self.stop_flag = False
        self.create_widgets()

    def create_widgets(self):
        # Title & Format Selector
        tk.Label(self.root, text="Image to EPUB/CBZ Converter", bg=Style.BG, fg=Style.FG, font=Style.FONT_TITLE).pack(pady=(10,0))
        fmt_frame = tk.Frame(self.root, bg=Style.BG)
        fmt_frame.pack()
        tk.Label(fmt_frame, text="Format:", bg=Style.BG, fg=Style.FG).pack(side="left", padx=(0,5))
        self.format = ttk.Combobox(fmt_frame, values=["EPUB", "CBZ"], state="readonly")
        self.format.set("EPUB")
        self.format.pack(side="left")

        # Folder list
        self.listbox = Listbox(self.root, bg=Style.LIST_BG, fg=Style.FG, selectmode='extended')
        self.listbox.pack(fill="both", expand=True, padx=20, pady=(10,0))
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind('<<Drop>>', self.drop_folders)

        # Buttons
        btn_frame = tk.Frame(self.root, bg=Style.BG)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Add Folders", command=self.add_folders).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Clear", command=self.clear_list).pack(side="left", padx=5)
        self.convert_btn = tk.Button(btn_frame, text="Convert", command=self.start_conversion, bg=Style.BTN_BG, fg="white")
        self.convert_btn.pack(side="left", padx=5)
        self.stop_btn = tk.Button(btn_frame, text="Cancel", command=self.cancel, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        # Logs
        self.logs = scrolledtext.ScrolledText(self.root, height=8, state="disabled", bg=Style.LIST_BG, fg=Style.FG, font=Style.FONT_MONO)
        self.logs.pack(fill="both", padx=20, pady=(0,10))

        # Progress bar
        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=(0,10))

    def add_folders(self):
        folder = filedialog.askdirectory()
        if folder and folder not in self.listbox.get(0, END):
            self.listbox.insert(END, folder)

    def drop_folders(self, event):
        paths = self.root.tk.splitlist(event.data)
        for p in paths:
            if os.path.isdir(p) and p not in self.listbox.get(0, END):
                self.listbox.insert(END, p)

    def clear_list(self):
        self.listbox.delete(0, END)

    def log(self, msg):
        self.logs.config(state="normal")
        self.logs.insert(END, msg + "\n")
        self.logs.see(END)
        self.logs.config(state="disabled")

    def cancel(self):
        self.stop_flag = True
        self.log("[!] Cancelling...")

    def update_progress(self, step):
        self.progress.step(step)

    def start_conversion(self):
        folders = self.listbox.get(0, END)
        if not folders:
            return messagebox.showwarning("No folders", "Please add folders to convert.")
        out_dir = filedialog.askdirectory(title="Select Output Folder")
        if not out_dir:
            return

        self.progress["value"] = 0
        self.progress["maximum"] = sum(len([f for f in os.listdir(folder) if f.lower().endswith(('jpg','jpeg','png','gif','bmp','webp'))]) for folder in folders)

        self.convert_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.stop_flag = False

        fmt = self.format.get()
        threading.Thread(target=self.convert_all, args=(folders, out_dir, fmt), daemon=True).start()

    def convert_all(self, folders, out_dir, fmt):
        for folder in folders:
            if self.stop_flag:
                break
            if fmt == "EPUB":
                create_epub(folder, out_dir, self.log, self.update_progress, lambda: self.stop_flag)
            else:
                create_cbz(folder, out_dir, self.log, self.update_progress, lambda: self.stop_flag)

        self.log("Done." if not self.stop_flag else "Cancelled.")
        self.convert_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

# --- Run App ---
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = App(root)
    root.mainloop()
