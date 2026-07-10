import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import threading
import sys
import os
import webbrowser
import ctypes
import json

from scripts import library_manager_v3 as lib_manager

if os.name == 'nt':
    myappid = 'JDHWOODS.ITCHLIBRARYAPP.USERGUI.3' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class ItchLibraryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Itch.io Library Manager")
        self.root.geometry("850x570") 
        self.root.configure(bg="#2d2d2d")

        try:
            self.root.iconbitmap(resource_path("app_icon.ico"))
        except Exception:
            pass

        self.manual_wait_event = threading.Event()

        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), borderwidth=1)
        style.map('TButton',
            foreground=[('active', 'white'), ('!active', 'white')],
            background=[('active', '#fa5c5c'), ('!active', '#ff2449')] 
        )
        
        self.btn_frame = tk.Frame(root, bg="#2d2d2d", pady=10)
        self.btn_frame.pack(side=tk.TOP, fill=tk.X)

        self.btn_full = ttk.Button(self.btn_frame, text="FULL UPDATE (AUTOMATIC)", command=self.run_full_update)
        self.btn_full.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)

        self.btn_update = ttk.Button(self.btn_frame, text="ADD NEW (MANUAL)", command=self.run_update_manual)
        self.btn_update.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.btn_finish_manual = ttk.Button(self.btn_frame, text="✔️ FINISH SCROLL", command=self.finish_manual_scroll)
        self.btn_finish_manual.pack_forget()
        
        tk.Label(self.btn_frame, text="|", bg="#2d2d2d", fg="#666").pack(side=tk.LEFT, padx=5)

        self.btn_fetch = ttk.Button(self.btn_frame, text="1. Fetch", command=self.run_fetch_only)
        self.btn_fetch.pack(side=tk.LEFT, padx=2)

        self.btn_scrape = ttk.Button(self.btn_frame, text="2. Scrape", command=self.run_scrape_only)
        self.btn_scrape.pack(side=tk.LEFT, padx=2)

        self.btn_html = ttk.Button(self.btn_frame, text="3. HTML", command=self.run_html_only)
        self.btn_html.pack(side=tk.LEFT, padx=2)

        self.log_label = tk.Label(root, text="Activity Log:", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 9))
        self.log_label.pack(anchor="w", padx=10)

        self.log_text = scrolledtext.ScrolledText(
            root, state='disabled', height=15, 
            bg="#1a1a1a", fg="#00ff00", font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        
        self.log_text.tag_config('INFO', foreground='#00ff00')
        self.log_text.tag_config('ERROR', foreground='#ff4444')

        self.bottom_frame = tk.Frame(root, bg="#2d2d2d", pady=5)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.btn_sync = ttk.Button(self.bottom_frame, text="☁️ Sync to Itch", command=self.show_sync_dialog)
        self.btn_sync.pack(side=tk.LEFT, padx=10)

        self.btn_import = ttk.Button(self.bottom_frame, text="📥 Import Public Collection", command=self.show_import_dialog)
        self.btn_import.pack(side=tk.LEFT, padx=10)

        self.btn_open_folder = ttk.Button(self.bottom_frame, text="Open Output Folder", command=self.open_folder)
        self.btn_open_folder.pack(side=tk.RIGHT, padx=10)

        self.btn_view_result = ttk.Button(self.bottom_frame, text="View Catalog", command=self.view_catalog)
        self.btn_view_result.pack(side=tk.RIGHT, padx=10)

        self.credits_label = tk.Label(
            root, text="Code by Joseph Woods - 2026", bg="#2d2d2d", fg="#555", font=("Segoe UI", 8)
        )
        self.credits_label.pack(side=tk.BOTTOM, pady=(0, 5))

        sys.stdout = TextRedirector(self.log_text, "INFO")
        sys.stderr = TextRedirector(self.log_text, "ERROR")

        print("Ready. Click 'FULL UPDATE (AUTOMATIC)' or 'ADD NEW (MANUAL)' to start.")

    def run_threaded(self, target_func):
        self.toggle_buttons(False)
        thread = threading.Thread(target=target_func, daemon=True)
        thread.start()

    def toggle_buttons(self, state):
        s = 'normal' if state else 'disabled'
        self.btn_full.state(['!disabled'] if state else ['disabled'])
        self.btn_update.state(['!disabled'] if state else ['disabled'])
        self.btn_fetch.state(['!disabled'] if state else ['disabled'])
        self.btn_scrape.state(['!disabled'] if state else ['disabled'])
        self.btn_html.state(['!disabled'] if state else ['disabled'])
        self.btn_sync.state(['!disabled'] if state else ['disabled'])
        self.btn_import.state(['!disabled'] if state else ['disabled'])

    def task_finished(self):
        self.toggle_buttons(True)
        self.btn_finish_manual.pack_forget()
        print("\n--- Task Complete ---")

    def confirm_popup(self):
        return messagebox.askyesno(
            "Itch Library Manager", 
            "The browser has finished scrolling.\n\n"
            "1. Check the browser window.\n"
            "2. Did it reach the very bottom?\n"
            "3. If not, scroll down manually now.\n\n"
            "Click YES to save the data.\n"
            "Click NO to abort."
        )

    def run_full_update(self):
        self.run_threaded(self._process_full)

    def _process_full(self):
        try:
            lib_manager.fetch_itch_library(gui_confirmation=self.confirm_popup, auto_scroll=True)
            lib_manager.run_scraper_conversion()
            lib_manager.generate_gallery()
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        self.task_finished()

    def run_update_manual(self):
        self.manual_wait_event.clear()
        self.run_threaded(self._process_update_manual)
        self.btn_finish_manual.pack(side=tk.LEFT, padx=5, after=self.btn_update)
        self.btn_finish_manual.state(['!disabled'])

    def finish_manual_scroll(self):
        self.btn_finish_manual.state(['disabled'])
        self.manual_wait_event.set()

    def _process_update_manual(self):
        try:
            lib_manager.fetch_itch_library(auto_scroll=False, manual_wait_event=self.manual_wait_event)
            lib_manager.run_scraper_conversion()
            lib_manager.generate_gallery()
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        self.task_finished()

    def run_fetch_only(self):
        self.run_threaded(lambda: [
            lib_manager.fetch_itch_library(gui_confirmation=self.confirm_popup, auto_scroll=True), 
            self.task_finished()
        ])

    def run_scrape_only(self):
        self.run_threaded(lambda: [lib_manager.run_scraper_conversion(), self.task_finished()])

    def run_html_only(self):
        self.run_threaded(lambda: [lib_manager.generate_gallery(), self.task_finished()])

    def show_sync_dialog(self):
        if not os.path.exists(lib_manager.collections_path):
            messagebox.showerror("Error", "collections.json not found in data folder. Nothing to sync.")
            return
            
        try:
            with open(lib_manager.collections_path, "r", encoding="utf-8") as f:
                col_db = json.load(f)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to read collections.json: {e}")
            return
            
        unique_cols = set()
        for tags in col_db.values():
            for t in tags.split(','):
                c = t.strip()
                if c and c != '[Hidden]':
                    unique_cols.add(c)
                    
        if not unique_cols:
            messagebox.showinfo("Sync", "No collections found to sync.")
            return

        sync_win = tk.Toplevel(self.root)
        sync_win.title("Select Collections to Sync")
        sync_win.geometry("350x400")
        sync_win.configure(bg="#2d2d2d")
        sync_win.grab_set()

        lbl_warn = tk.Label(sync_win, text="NOTE: This is a ONE-WAY transfer\nfrom your local app to itch.io!", bg="#2d2d2d", fg="#ff4444", font=("Segoe UI", 10, "bold"))
        lbl_warn.pack(side=tk.TOP, pady=10)

        lbl_inst = tk.Label(sync_win, text="Select collections to upload:", bg="#2d2d2d", fg="#e0e0e0")
        lbl_inst.pack(side=tk.TOP)

        def start_sync():
            selected = [col for col, var in checkbox_vars.items() if var.get()]
            sync_win.destroy()
            if selected:
                self.run_threaded(lambda: self._process_sync(selected))

        btn_start = ttk.Button(sync_win, text="Start Sync", command=start_sync)
        btn_start.pack(side=tk.BOTTOM, pady=15)

        frame_cb = tk.Frame(sync_win, bg="#1a1a1a", bd=2, relief=tk.SUNKEN)
        frame_cb.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=20, pady=10)

        canvas = tk.Canvas(frame_cb, bg="#1a1a1a", highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame_cb, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#1a1a1a")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        checkbox_vars = {}
        for col in sorted(unique_cols):
            var = tk.BooleanVar(value=True)
            checkbox_vars[col] = var
            cb = tk.Checkbutton(scrollable_frame, text=col, variable=var, bg="#1a1a1a", fg="#00ff00", selectcolor="#2d2d2d", activebackground="#1a1a1a", activeforeground="#00ff00")
            cb.pack(anchor="w", padx=5, pady=2)

    def _process_sync(self, selected_collections):
        try:
            lib_manager.sync_collections_to_itch(selected_collections)
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        self.task_finished()
        
    def show_import_dialog(self):
        url = simpledialog.askstring(
            "Import Collection", 
            "Enter the public itch.io collection URL:\n(Note: The collection MUST be public!)",
            parent=self.root
        )
        if url and url.strip():
            self.run_threaded(lambda: self._process_import(url.strip()))

    def _process_import(self, url):
        try:
            lib_manager.import_public_collection(url)
            lib_manager.generate_gallery()
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        self.task_finished()

    def open_folder(self):
        os.startfile(os.getcwd())

    def view_catalog(self):
        path = os.path.join(os.getcwd(), "itch_catalog.html")
        if os.path.exists(path):
            webbrowser.open(path)
        else:
            messagebox.showerror("Error", "Catalog file not found. Run the update first!")

class TextRedirector:
    def __init__(self, widget, tag="INFO"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        try:
            self.widget.configure(state='normal')
            self.widget.insert(tk.END, str, (self.tag))
            self.widget.see(tk.END)
            self.widget.configure(state='disabled')
        except:
            pass
    
    def flush(self):
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ItchLibraryApp(root)
    root.mainloop()