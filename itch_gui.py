import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import sys
import os
import webbrowser
import ctypes

# This is the script that actually does the work
from scripts import library_manager_v3 as lib_manager

if os.name == 'nt':
    myappid = 'JDHWOODS.ITCHLIBRARYAPP.USERGUI.2' # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ItchLibraryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Itch.io Library Manager")
        self.root.geometry("700x550")
        self.root.configure(bg="#2d2d2d")

        try:
            # We use the helper function to find the icon file
            self.root.iconbitmap(resource_path("app_icon.ico"))
        except Exception:
            # If the icon is missing, just ignore it so the app doesn't crash
            pass

        # Set up the visual style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Make the buttons look like Itch.io (Pink/Red)
        style.configure('TButton', font=('Segoe UI', 10, 'bold'), borderwidth=1)
        style.map('TButton',
            foreground=[('active', 'white'), ('!active', 'white')],
            background=[('active', '#fa5c5c'), ('!active', '#ff2449')] 
        )
        
        # Top bar for the buttons
        self.btn_frame = tk.Frame(root, bg="#2d2d2d", pady=10)
        self.btn_frame.pack(side=tk.TOP, fill=tk.X)

        # The big "Do Everything" button
        self.btn_full = ttk.Button(self.btn_frame, text="RUN FULL UPDATE", command=self.run_full_update)
        self.btn_full.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)
        
        # Divider line
        tk.Label(self.btn_frame, text="|", bg="#2d2d2d", fg="#666").pack(side=tk.LEFT, padx=5)

        # Individual step buttons (so you can skip bits if you fiddle with files yourself, or wanna debug)
        self.btn_fetch = ttk.Button(self.btn_frame, text="1. Fetch Library", command=self.run_fetch_only)
        self.btn_fetch.pack(side=tk.LEFT, padx=5)

        self.btn_scrape = ttk.Button(self.btn_frame, text="2. Scrape CSV", command=self.run_scrape_only)
        self.btn_scrape.pack(side=tk.LEFT, padx=5)

        self.btn_html = ttk.Button(self.btn_frame, text="3. Generate HTML", command=self.run_html_only)
        self.btn_html.pack(side=tk.LEFT, padx=5)

        # Log window label
        self.log_label = tk.Label(root, text="Activity Log:", bg="#2d2d2d", fg="#aaa", font=("Segoe UI", 9))
        self.log_label.pack(anchor="w", padx=10)

        # The main text box where print() statements go
        self.log_text = scrolledtext.ScrolledText(
            root, state='disabled', height=15, 
            bg="#1a1a1a", fg="#00ff00", font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        # Colors for different log levels (if needed)
        self.log_text.tag_config('INFO', foreground='#00ff00')
        self.log_text.tag_config('ERROR', foreground='#ff4444')

        # Bottom bar for file actions
        self.bottom_frame = tk.Frame(root, bg="#2d2d2d", pady=5)
        self.bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.btn_open_folder = ttk.Button(self.bottom_frame, text="Open Output Folder", command=self.open_folder)
        self.btn_open_folder.pack(side=tk.RIGHT, padx=10)
        # I hate TKINTER so much
        self.btn_view_result = ttk.Button(self.bottom_frame, text="View Catalog", command=self.view_catalog)
        self.btn_view_result.pack(side=tk.RIGHT, padx=10)

        # Wow output so we can see what's going on! Hijack print() and send it to our text box instead (Wish I added this earlier, this was added LAST. Good job me)
        sys.stdout = TextRedirector(self.log_text, "INFO")
        sys.stderr = TextRedirector(self.log_text, "ERROR")

        print("Ready. Click 'RUN FULL UPDATE' to start.")

    # --- Threading Stuff (So the GUI doesn't freeze and freak out like the first time I ran this) ---
    
    def run_threaded(self, target_func):
        self.toggle_buttons(False)
        # Daemon=True means the thread dies if we close the window preventing weird hangs
        thread = threading.Thread(target=target_func, daemon=True)
        thread.start()

    def toggle_buttons(self, state):
        s = 'normal' if state else 'disabled'
        self.btn_full['state'] = s
        self.btn_fetch['state'] = s
        self.btn_scrape['state'] = s
        self.btn_html['state'] = s

    def task_finished(self):
        self.toggle_buttons(True)
        print("\n--- Task Complete ---")

    # --- Button Functions ---
    
    def confirm_popup(self):
        # This is passed to the library manager to pause execution
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
            # Step 1: Get the HTML
            lib_manager.fetch_itch_library(gui_confirmation=self.confirm_popup)
            # Step 2: Convert to CSV
            lib_manager.run_scraper_conversion()
            # Step 3: Make the Gallery
            lib_manager.generate_gallery()
        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        self.task_finished()

    # Individual wrappers for the small buttons
    def run_fetch_only(self):
        self.run_threaded(lambda: [
            lib_manager.fetch_itch_library(gui_confirmation=self.confirm_popup), 
            self.task_finished()
        ])

    def run_scrape_only(self):
        self.run_threaded(lambda: [
            lib_manager.run_scraper_conversion(), 
            self.task_finished()
        ])

    def run_html_only(self):
        self.run_threaded(lambda: [
            lib_manager.generate_gallery(), 
            self.task_finished()
        ])

    # Helper buttons that Help
    def open_folder(self):
        os.startfile(os.getcwd())

    def view_catalog(self):
        path = os.path.join(os.getcwd(), "itch_catalog.html")
        if os.path.exists(path):
            webbrowser.open(path)
        else:
            messagebox.showerror("Error", "Catalog file not found. Run the update first!")

# Helper class to redirect stdout
class TextRedirector:
    def __init__(self, widget, tag="INFO"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        try:
            self.widget.configure(state='normal')
            self.widget.insert(tk.END, str, (self.tag))
            self.widget.see(tk.END) # Auto-scroll to bottom
            self.widget.configure(state='disabled')
        except:
            pass # Ignore errors if window is closing
    
    def flush(self):
        pass

if __name__ == "__main__":
    root = tk.Tk()
    app = ItchLibraryApp(root)
    root.mainloop()
