import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Listbox, END, ttk, PhotoImage
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from PIL import Image
from ebooklib import epub
from io import BytesIO
import zipfile
import threading

# --- UI Themes ---
class Style:
    THEMES = {
        'light': {
            'BG': '#ffffff', 'FG': '#000000', 'LIST_BG': '#f0f0f0', 'PLACEHOLDER_FG': '#777777',
            'BTN_BG': '#88B6F2', 'BTN_FG': '#ffffff', 'BTN_ACTIVE': '#9BC1F2',
            'BTN_DISABLED_FG': '#aaaaaa',
            'FONT': ("Segoe UI", 12), 'FONT_TITLE': ("Segoe UI", 14, "bold"), 'FONT_MONO': ("Consolas", 10)
        },
        'dark': {
            'BG': '#2b2b2b', 'FG': '#e0e0e0', 'LIST_BG': '#3c3f41', 'PLACEHOLDER_FG': '#aaaaaa',
            'BTN_BG': '#888888', 'BTN_FG': '#ffffff', 'BTN_ACTIVE': '#666666',
            'BTN_DISABLED_FG': '#aaaaaa',
            'FONT': ("Segoe UI", 12), 'FONT_TITLE': ("Segoe UI", 14, "bold"), 'FONT_MONO': ("Consolas", 10)
        }
    }

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
    total = len(files)
    for idx, img in enumerate(files):
        if stop_flag(): return
        p = os.path.join(folder, img)
        data = process_image(p)
        if not data: continue

        img_name = f'image_{idx:03d}.jpg'
        item = epub.EpubItem(uid=f'img_{idx}', file_name=f'images/{img_name}', media_type='image/jpeg', content=data)
        book.add_item(item)

        html = f'<html><body style="background-color:black;"><img src="images/{img_name}" style="max-width:100%;max-height:100%;display:block;margin:auto;"/></body></html>'
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
        self.theme = 'dark'
        self.style = Style.THEMES[self.theme]

        self.root.title("Images to E-Books Converter")
        self.root.geometry("800x600")
        self.root.configure(bg=self.style['BG'])

        self.stop_flag = False
        self.progress_total = 0
        self.setup_widgets()

    def setup_widgets(self):
        top_frame = tk.Frame(self.root, bg=self.style['BG'])
        top_frame.pack(fill='x', padx=10, pady=10)

        tk.Label(top_frame, text="Images to E-Books Converter", font=self.style['FONT_TITLE'], bg=self.style['BG'], fg=self.style['FG']).pack(side='left')

        self.theme_btn = tk.Button(top_frame, text="🌙" if self.theme == 'light' else "💡", command=self.toggle_theme, bg=self.style['BG'], fg=self.style['FG'], bd=0, font=("Segoe UI", 12))
        self.theme_btn.pack(side='right')

        fmt_frame = tk.Frame(self.root, bg=self.style['BG'])
        fmt_frame.pack()
        tk.Label(fmt_frame, text="Format:", bg=self.style['BG'], fg=self.style['FG'], font=self.style['FONT']).pack(side="left")
        self.format = ttk.Combobox(fmt_frame, values=["EPUB", "CBZ"], state="readonly")
        self.format.set("EPUB")
        self.format.pack(side="left", padx=5)

        tk.Label(self.root, text="EPUB - Best for text-centric books. CBZ - Best for comics and manga.", bg=self.style['BG'], fg=self.style['FG'], font=("Segoe UI", 9)).pack(pady=5)

        self.listbox = Listbox(self.root, bg=self.style['LIST_BG'], fg=self.style['FG'], selectmode='extended')
        self.listbox.pack(fill='both', expand=True, padx=20, pady=(0, 5))
        self.listbox.drop_target_register(DND_FILES)
        self.listbox.dnd_bind('<<Drop>>', self.drop_folders)

        self.placeholder = tk.Label(self.listbox, text="Drop folders here", fg=self.style['PLACEHOLDER_FG'], bg=self.style['LIST_BG'], font=self.style['FONT'])
        self.placeholder.place(relx=0.5, rely=0.5, anchor='center')

        btn_frame = tk.Frame(self.root, bg=self.style['BG'])
        btn_frame.pack(pady=5)
        self.btn_add = self.make_button(btn_frame, "Add Folders", self.add_folders)
        self.btn_clear = self.make_button(btn_frame, "Clear List", self.clear_list)
        self.btn_logs = self.make_button(btn_frame, "Clear Logs", self.clear_logs)
        self.btn_convert = self.make_button(btn_frame, "Start Converts", self.start_conversion)
        self.btn_cancel = self.make_button(btn_frame, "Cancel", self.cancel, state="disabled")

        self.logs = scrolledtext.ScrolledText(self.root, height=6, state="disabled", bg=self.style['LIST_BG'], fg=self.style['FG'], font=self.style['FONT_MONO'])
        self.logs.pack(fill="both", padx=20, pady=(0,5))

        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", padx=20, pady=(0,10))

    def make_button(self, parent, text, command, **kwargs):
        btn = tk.Button(parent, text=text, command=command, bg=self.style['BTN_BG'], fg=self.style['BTN_FG'], font=self.style['FONT'], bd=0, padx=12, pady=6, relief="raised", highlightthickness=0, **kwargs)
        btn.configure(highlightbackground=self.style['BTN_BG'])
        btn.pack(side="left", padx=6, pady=4)
        btn.configure(borderwidth=0, highlightthickness=0)
        btn.bind("<Enter>", lambda e: btn.config(bg=self.style['BTN_ACTIVE']))
        btn.bind("<Leave>", lambda e: btn.config(bg=self.style['BTN_BG']))
        return btn

    def toggle_theme(self):
        self.theme = 'light' if self.theme == 'dark' else 'dark'
        self.style = Style.THEMES[self.theme]
        self.refresh_theme()

    def refresh_theme(self):
        self.root.configure(bg=self.style['BG'])
        for widget in self.root.winfo_children():
            widget.destroy()
        self.setup_widgets()

    def add_folders(self):
        folder = filedialog.askdirectory()
        if folder and folder not in self.listbox.get(0, END):
            self.listbox.insert(END, folder)
        self.update_placeholder()

    def drop_folders(self, event):
        paths = self.root.tk.splitlist(event.data)
        for p in paths:
            if os.path.isdir(p) and p not in self.listbox.get(0, END):
                self.listbox.insert(END, p)
        self.update_placeholder()

    def update_placeholder(self):
        self.placeholder.place_forget() if self.listbox.size() else self.placeholder.place(relx=0.5, rely=0.5, anchor='center')

    def clear_list(self):
        self.listbox.delete(0, END)
        self.update_placeholder()

    def clear_logs(self):
        self.logs.config(state="normal")
        self.logs.delete("1.0", END)
        self.logs.config(state="disabled")

    def cancel(self):
        self.stop_flag = True
        self.log("[!] Cancelling...")

    def log(self, msg):
        self.logs.config(state="normal")
        self.logs.insert(END, msg + "\n")
        self.logs.see(END)
        self.logs.config(state="disabled")
        if msg in ["Done.", "Cancelled."]:
            self.progress["value"] = 0
            self.btn_convert.config(text="Start Converts")

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

        self.btn_convert.config(state="disabled", text="Converting...", disabledforeground=self.style['BTN_DISABLED_FG'])
        self.btn_cancel.config(state="normal")
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
        self.btn_convert.config(state="normal", text="Start Converts")
        self.btn_cancel.config(state="disabled")

# --- Run App ---
if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = App(root)
    root.mainloop()
