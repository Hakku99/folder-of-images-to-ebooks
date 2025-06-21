import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Listbox, END, font as tkFont, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
from PIL import Image
import ebooklib
from ebooklib import epub
from io import BytesIO
import threading
import traceback

# --- COLOR & FONT DEFINITIONS ---
class Style:
    BACKGROUND = '#2b2b2b'
    FOREGROUND = '#dcdcdc'
    LIST_BG = '#3c3f41'
    PLACEHOLDER_FG = '#6e7072'
    BUTTON_BG = '#007acc'
    BUTTON_FG = '#ffffff'
    BUTTON_HOVER = '#005f9e'
    SUCCESS_COLOR = '#4caf50'
    ERROR_COLOR = '#f44336'
    
    FONT_FAMILY = "Segoe UI"
    FONT_NORMAL = (FONT_FAMILY, 10)
    FONT_BOLD = (FONT_FAMILY, 11, "bold")
    FONT_TITLE = (FONT_FAMILY, 16, "bold")
    FONT_PLACEHOLDER = (FONT_FAMILY, 14, "italic")

# --- CORE CONVERSION LOGIC ---
def get_processed_image_bytes(image_path, log_callback):
    """
    Processes an image to bytes.
    - If the image is a JPEG, its original data is preserved to prevent re-compression.
    - If it's another format (PNG, etc.), it's converted to a maximum-quality JPEG.
    """
    try:
        with Image.open(image_path) as img:
            # For existing JPEGs, read raw bytes to avoid any quality loss from re-saving.
            if img.format == 'JPEG':
                log_callback(f"    - Preserving original JPEG: {os.path.basename(image_path)}")
                with open(image_path, 'rb') as f_in:
                    return f_in.read()
            
            # For non-JPEG images (PNG, WEBP, etc.), convert to a high-quality JPEG.
            else:
                log_callback(f"    - Converting to max-quality JPEG: {os.path.basename(image_path)}")
                # Ensure image is in a saveable mode (RGB)
                if img.mode not in ('RGB', 'L'): # 'L' is for grayscale
                    img = img.convert("RGB")
                
                buffer = BytesIO()
                # Use quality=100 and subsampling=0 for the highest possible quality.
                img.save(buffer, format='JPEG', quality=100, subsampling=0)
                return buffer.getvalue()

    except Exception as e:
        log_callback(f"[ERROR] Could not process image file: {os.path.basename(image_path)}", Style.ERROR_COLOR)
        log_callback(traceback.format_exc(), Style.ERROR_COLOR)
        return None

def create_epub_from_folder(folder_path, output_dir, log_callback, progress_callback):
    folder_name = os.path.basename(folder_path.rstrip("/\\"))
    log_callback(f"--- Processing: {folder_name} ---")

    try:
        image_files = sorted(
            [f for f in os.listdir(folder_path) if os.path.splitext(f)[1].lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']],
            key=lambda f: int(''.join(filter(str.isdigit, f))) if any(char.isdigit() for char in f) else -1
        )

        if not image_files:
            log_callback(f"[WARNING] No valid images found in {folder_name}. Skipping.")
            progress_callback(0, is_folder_complete=True)
            return

        log_callback(f"  Found {len(image_files)} images.")

        book = epub.EpubBook()
        book.set_identifier(f'image-epub-{folder_name}')
        book.set_title(folder_name)
        book.set_language('en')
        book.add_author('Image to EPUB Converter')

        epub_pages = []

        for idx, image_name in enumerate(image_files):
            # No need to log here, the get_processed_image_bytes function will log its action.
            image_path = os.path.join(folder_path, image_name)
            
            image_data = get_processed_image_bytes(image_path, log_callback)
            if not image_data:
                continue

            new_filename = os.path.splitext(image_name)[0] + '.jpg'
            
            epub_img = epub.EpubItem(uid=f'image_{idx}', file_name=f'images/{new_filename}', media_type='image/jpeg', content=image_data)
            book.add_item(epub_img)

            html_content = f'<html><head><title>Page {idx+1}</title><style>body{{margin:0;padding:0;}}img{{width:100vw;height:100vh;object-fit:contain;}}</style></head><body><img src="images/{new_filename}" alt="{new_filename}"/></body></html>'
            page = epub.EpubHtml(title=f'Page {idx+1}', file_name=f'page_{idx+1}.xhtml', content=html_content)
            
            page.properties.extend(['rendition:layout-pre-paginated', 'rendition:orientation-landscape', 'rendition:spread-both'])
            
            book.add_item(page)
            epub_pages.append(page)
            progress_callback(1, is_folder_complete=False)

        if not epub_pages:
            log_callback(f"[ERROR] No pages could be created for {folder_name}. Aborting.", Style.ERROR_COLOR)
            progress_callback(0, is_folder_complete=True)
            return

        book.spine = epub_pages
        book.toc = tuple(epub_pages)
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        output_path = os.path.join(output_dir, f"{folder_name}.epub")
        log_callback(f"  Writing EPUB file to: {output_path}")
        epub.write_epub(output_path, book, {})
        log_callback(f"[SUCCESS] EPUB created for {folder_name}.\n", Style.SUCCESS_COLOR)
        progress_callback(0, is_folder_complete=True)

    except Exception as e:
        log_callback(f"[FATAL ERROR] Failed to create EPUB for {folder_name}.", Style.ERROR_COLOR)
        log_callback(traceback.format_exc(), Style.ERROR_COLOR)
        progress_callback(0, is_folder_complete=True)

# --- GUI Application (UI is unchanged) ---
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Image to EPUB Converter")
        self.root.geometry("800x650")
        self.root.configure(bg=Style.BACKGROUND)
        self.root.minsize(600, 500)
        
        self.create_widgets()
        self.configure_styles()
        self.bind_events()
        self.check_list_placeholder()

    def create_widgets(self):
        top_frame = tk.Frame(self.root, bg=Style.BACKGROUND)
        top_frame.pack(side="top", fill="x", padx=20, pady=(20, 10))

        center_frame = tk.Frame(self.root, bg=Style.BACKGROUND)
        center_frame.pack(fill="both", expand=True, padx=20)
        center_frame.grid_rowconfigure(1, weight=1)
        center_frame.grid_columnconfigure(0, weight=1)
        
        bottom_frame = tk.Frame(self.root, bg=Style.BACKGROUND)
        bottom_frame.pack(side="bottom", fill="x", padx=20, pady=(10, 20))
        
        title_label = tk.Label(top_frame, text="Image to EPUB Converter", fg=Style.FOREGROUND, bg=Style.BACKGROUND, font=Style.FONT_TITLE)
        title_label.pack()

        list_container = tk.Frame(center_frame, bg=Style.LIST_BG)
        list_container.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)
        
        self.listbox = Listbox(list_container, selectmode='extended', bg=Style.LIST_BG, fg=Style.FOREGROUND, font=Style.FONT_NORMAL, relief="flat", borderwidth=0, highlightthickness=0)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.drop_target_register(DND_FILES)
        
        self.placeholder_label = tk.Label(list_container, text="Drag & Drop Folders Here", font=Style.FONT_PLACEHOLDER, bg=Style.LIST_BG, fg=Style.PLACEHOLDER_FG)
        
        self.log_text = scrolledtext.ScrolledText(center_frame, state='disabled', wrap=tk.WORD, bg=Style.LIST_BG, fg=Style.FOREGROUND, font=("Consolas", 9), relief="flat", borderwidth=0, highlightthickness=0, height=10)
        self.log_text.grid(row=2, column=0, sticky="nsew")

        button_container = tk.Frame(bottom_frame, bg=Style.BACKGROUND)
        button_container.pack(fill="x", expand=True, pady=(0, 10))
        
        self.add_btn = tk.Button(button_container, text="Add Folders", command=self.add_folders)
        self.add_btn.pack(side="left", expand=True, padx=(0, 5))
        
        self.clear_list_btn = tk.Button(button_container, text="Clear List", command=self.clear_list)
        self.clear_list_btn.pack(side="left", expand=True, padx=5)

        self.clear_logs_btn = tk.Button(button_container, text="Clear Logs", command=self.clear_logs)
        self.clear_logs_btn.pack(side="left", expand=True, padx=5)

        self.convert_btn = tk.Button(button_container, text="Convert to EPUB", command=self.start_conversion)
        self.convert_btn.pack(side="left", expand=True, padx=(5, 0))

        s = ttk.Style()
        s.theme_use('clam')
        s.configure("green.Horizontal.TProgressbar", foreground=Style.SUCCESS_COLOR, background=Style.SUCCESS_COLOR, troughcolor=Style.LIST_BG, bordercolor=Style.LIST_BG, lightcolor=Style.SUCCESS_COLOR, darkcolor=Style.SUCCESS_COLOR)
        self.progress_bar = ttk.Progressbar(bottom_frame, style="green.Horizontal.TProgressbar", orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", expand=True, ipady=2)

    def configure_styles(self):
        for btn in [self.add_btn, self.clear_list_btn, self.clear_logs_btn, self.convert_btn]:
            btn.config(font=Style.FONT_BOLD, bg=Style.BUTTON_BG, fg=Style.BUTTON_FG, relief="flat", pady=5, activebackground=Style.BUTTON_HOVER, activeforeground=Style.BUTTON_FG)
        
        self.log_text.tag_config('error', foreground=Style.ERROR_COLOR)
        self.log_text.tag_config('success', foreground=Style.SUCCESS_COLOR)
        self.log("Welcome! Drag & drop folders into the area above or use the 'Add Folders' button.")
        
    def bind_events(self):
        self.listbox.dnd_bind('<<Drop>>', self.on_drop)
        for btn in [self.add_btn, self.clear_list_btn, self.clear_logs_btn, self.convert_btn]:
            btn.bind("<Enter>", self.on_button_enter)
            btn.bind("<Leave>", self.on_button_leave)
            
    def check_list_placeholder(self, *args):
        if self.listbox.size() == 0:
            self.placeholder_label.place(in_=self.listbox, relx=0.5, rely=0.5, anchor="center")
        else:
            self.placeholder_label.place_forget()

    def on_button_enter(self, e): e.widget.config(bg=Style.BUTTON_HOVER)
    def on_button_leave(self, e): e.widget.config(bg=Style.BUTTON_BG)
        
    def on_drop(self, event):
        dropped_items = self.root.tk.splitlist(event.data)
        count = 0
        for item in dropped_items:
            if os.path.isdir(item) and item not in self.listbox.get(0, END):
                self.listbox.insert(END, item)
                count += 1
        if count > 0:
            self.log(f"[INFO] Added {count} new folder(s) via drag and drop.")
            self.check_list_placeholder()

    def add_folders(self):
        path = filedialog.askdirectory(title="Select a Folder")
        if path and path not in self.listbox.get(0, END):
            self.listbox.insert(END, path)
            self.log(f"[INFO] Added folder: {path}")
            self.check_list_placeholder()

    def clear_list(self):
        self.listbox.delete(0, END)
        self.log("[INFO] Folder list cleared.")
        self.check_list_placeholder()

    def clear_logs(self):
        self.log_text.config(state='normal')
        self.log_text.delete('1.0', tk.END)
        self.log_text.config(state='disabled')
        self.log("Welcome! Drag & drop folders into the area above or use the 'Add Folders' button.")

    def log(self, message, tag=None):
        def _log():
            self.log_text.config(state='normal')
            self.log_text.insert(END, message + '\n', tag)
            self.log_text.config(state='disabled')
            self.log_text.see(END)
        self.root.after(0, _log)

    def start_conversion(self):
        folders = self.listbox.get(0, END)
        if not folders:
            messagebox.showwarning("No Folders", "Please add folders to the list before converting.")
            return

        output_dir = filedialog.askdirectory(title="Select a Folder to Save the EPUB Files")
        if not output_dir:
            return

        num_folders = len(folders)
        confirmation_message = (
            f"You are about to convert {num_folders} folder(s).\n\n"
            f"Output Location:\n{output_dir}\n\n"
            "Do you want to proceed?"
        )
        if not messagebox.askokcancel("Confirm Conversion", confirmation_message):
            self.log("[INFO] Conversion cancelled by user.")
            return

        self.convert_btn.config(state=tk.DISABLED, text="Converting...")
        self.clear_logs()
        
        self.total_images = sum(len([f for f in os.listdir(p) if os.path.splitext(f)[1].lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']]) for p in folders)
        self.total_folders = len(folders)
        self.folders_processed = 0
        self.progress_bar["maximum"] = self.total_images if self.total_images > 0 else 1
        self.progress_bar["value"] = 0
        
        threading.Thread(target=self.run_conversion_thread, args=(folders, output_dir), daemon=True).start()

    def update_progress(self, image_amount, is_folder_complete=False):
        def _update():
            self.progress_bar.step(image_amount)
            if is_folder_complete:
                self.folders_processed += 1
                if self.folders_processed == self.total_folders and self.total_images == 0:
                     self.progress_bar["value"] = self.progress_bar["maximum"]

        self.root.after(0, _update)
        
    def run_conversion_thread(self, folders, output_dir):
        self.log(f"--- Starting Conversion Process ---")
        self.log(f"Output Directory: {output_dir}\n")
        for folder_path in folders:
            create_epub_from_folder(folder_path, output_dir, self.log, self.update_progress)
        
        self.root.after(0, self.conversion_finished)

    def conversion_finished(self):
        self.log("--- All Conversions Attempted ---", 'success')
        messagebox.showinfo("Process Complete", "Conversion process finished! Please check the log for details on each folder.")
        self.convert_btn.config(state=tk.NORMAL, text="Convert to EPUB")
        self.progress_bar["value"] = self.progress_bar["maximum"]

if __name__ == "__main__":
    root = TkinterDnD.Tk()
    app = App(root)
    root.mainloop()
