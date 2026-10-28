
import os
import sys
import shutil
import threading
import queue
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import pytesseract
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    import pandas as pd
except ImportError as e:
    raise SystemExit("Missing packages. Run: pip install -r requirements.txt")

SUPPORTED = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}

LANGUAGES = {
    "English": "eng",
    "Bengali": "ben",
    "Hindi": "hin",
    "English + Bengali": "eng+ben",
    "English + Hindi": "eng+hin",
    "Bengali + Hindi": "ben+hin",
    "English + Bengali + Hindi": "eng+ben+hin",
}

COMMON_TESSERACT_PATHS = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]

def find_tesseract():
    p = shutil.which("tesseract")
    if p:
        return p
    for p in COMMON_TESSERACT_PATHS:
        if Path(p).exists():
            return p
    try:
        import winreg
        for root, keyname in [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Tesseract-OCR"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Tesseract-OCR"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Tesseract-OCR")]:
            try:
                with winreg.OpenKey(root, keyname) as k:
                    d,_=winreg.QueryValueEx(k,"InstallDir")
                    p=Path(d)/"tesseract.exe"
                    if p.exists(): return str(p)
            except Exception: pass
    except Exception: pass
    return None

class OCRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Multilingual OCR Tool - English + Bengali + Hindi")
        self.geometry("1050x720")
        self.minsize(900, 620)
        self.stop_event = threading.Event()
        self.msg_queue = queue.Queue()
        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.lang_var = tk.StringVar(value="English + Bengali + Hindi")
        self.accuracy_var = tk.BooleanVar(value=True)
        self.tess_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self._build_ui()
        self._auto_detect_tesseract()
        self.after(100, self._poll_queue)

    def _build_ui(self):
        style = ttk.Style(self)
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass

        header = tk.Frame(self, bg="#102f5f", height=82)
        header.pack(fill="x")
        tk.Label(header, text="MULTILINGUAL OCR TOOL",
                 font=("Segoe UI", 24, "bold"), fg="white", bg="#102f5f").pack(pady=(13,0))
        tk.Label(header, text="English + Bengali + Hindi",
                 font=("Segoe UI", 12, "bold"), fg="#ffd42a", bg="#102f5f").pack()

        main = ttk.Frame(self, padding=18)
        main.pack(fill="both", expand=True)

        # Folder selection
        ttk.Label(main, text="Step 1: Select Image Folder", font=("Segoe UI", 11, "bold")).grid(row=0, column=0, sticky="w", pady=(0,5))
        ttk.Entry(main, textvariable=self.input_var).grid(row=1, column=0, sticky="ew", padx=(0,8))
        ttk.Button(main, text="Browse", command=self.choose_input).grid(row=1, column=1, sticky="ew")

        ttk.Label(main, text="Step 2: Select Output Folder", font=("Segoe UI", 11, "bold")).grid(row=2, column=0, sticky="w", pady=(18,5))
        ttk.Entry(main, textvariable=self.output_var).grid(row=3, column=0, sticky="ew", padx=(0,8))
        ttk.Button(main, text="Browse", command=self.choose_output).grid(row=3, column=1, sticky="ew")

        options = ttk.LabelFrame(main, text="Options", padding=12)
        options.grid(row=4, column=0, columnspan=2, sticky="ew", pady=18)
        ttk.Label(options, text="Language:").grid(row=0, column=0, sticky="w")
        ttk.Combobox(options, textvariable=self.lang_var, values=list(LANGUAGES),
                     state="readonly", width=34).grid(row=0, column=1, sticky="w", padx=10)
        ttk.Checkbutton(options, text="Improve Accuracy (slower)", variable=self.accuracy_var).grid(row=1, column=1, sticky="w", pady=(10,0))

        ttk.Label(options, text="Tesseract:").grid(row=2, column=0, sticky="w", pady=(10,0))
        ttk.Entry(options, textvariable=self.tess_var).grid(row=2, column=1, sticky="ew", padx=10, pady=(10,0))
        ttk.Button(options, text="Browse / Detect", command=self.choose_tesseract).grid(row=2, column=2, padx=5, pady=(10,0))
        self.tess_status = ttk.Label(options, text="Checking Tesseract...")
        self.tess_status.grid(row=3, column=1, columnspan=2, sticky="w", padx=10, pady=5)
        options.columnconfigure(1, weight=1)

        buttons = ttk.Frame(main)
        buttons.grid(row=5, column=0, columnspan=2, sticky="ew")
        self.start_btn = tk.Button(buttons, text="🚀  START OCR", command=self.start,
                                    bg="#25a33a", fg="white", font=("Segoe UI", 11, "bold"),
                                    relief="flat", padx=18, pady=10)
        self.start_btn.pack(side="left", padx=(0,10))
        self.stop_btn = tk.Button(buttons, text="✕  STOP", command=self.stop,
                                  bg="#e85c5c", fg="white", font=("Segoe UI", 11, "bold"),
                                  relief="flat", padx=25, pady=10, state="disabled")
        self.stop_btn.pack(side="left")

        ttk.Label(main, text="Progress", font=("Segoe UI", 10, "bold")).grid(row=6, column=0, columnspan=2, sticky="w", pady=(18,5))
        ttk.Progressbar(main, variable=self.progress_var, maximum=100).grid(row=7, column=0, sticky="ew", padx=(0,8))
        ttk.Label(main, textvariable=self.status_var).grid(row=7, column=1, sticky="w")

        log_frame = ttk.LabelFrame(main, text="Activity Log", padding=8)
        log_frame.grid(row=8, column=0, columnspan=2, sticky="nsew", pady=(15,0))
        self.log = tk.Text(log_frame, height=18, wrap="word", font=("Consolas", 9))
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        self.log.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        main.columnconfigure(0, weight=1)
        main.rowconfigure(8, weight=1)

    def _auto_detect_tesseract(self):
        path = find_tesseract()
        if path:
            self.tess_var.set(path)
            pytesseract.pytesseract.tesseract_cmd = path
            try:
                v = str(pytesseract.get_tesseract_version()).splitlines()[0]
                self.tess_status.config(text=f"✓ Tesseract detected: {path} | {v}", foreground="green")
                self.log_msg(f"[INFO] Tesseract detected automatically: {path}")
            except Exception as e:
                self.tess_status.config(text=f"⚠ Tesseract found but cannot run: {e}", foreground="#b36b00")
        else:
            self.tess_status.config(text="✗ Not detected. Click Browse / Detect and select tesseract.exe.", foreground="red")

    def choose_tesseract(self):
        p = filedialog.askopenfilename(title="Select tesseract.exe", filetypes=[("Tesseract executable", "tesseract.exe"), ("All files", "*.*")])
        if p:
            self.tess_var.set(p)
            pytesseract.pytesseract.tesseract_cmd = p
            try:
                v = str(pytesseract.get_tesseract_version()).splitlines()[0]
                self.tess_status.config(text=f"✓ Tesseract ready: {p} | {v}", foreground="green")
            except Exception as e:
                self.tess_status.config(text=f"✗ Cannot run selected Tesseract: {e}", foreground="red")
                messagebox.showerror("Tesseract", str(e))

    def choose_input(self):
        p = filedialog.askdirectory(title="Select folder containing images")
        if p:
            self.input_var.set(p)
            if not self.output_var.get():
                self.output_var.set(str(Path(p) / "OCR_Output"))

    def choose_output(self):
        p = filedialog.askdirectory(title="Select output folder")
        if p:
            self.output_var.set(p)

    def log_msg(self, text):
        self.msg_queue.put(("log", text))

    def start(self):
        inp = Path(self.input_var.get().strip())
        out = Path(self.output_var.get().strip() or (inp / "OCR_Output"))
        if not inp.exists() or not inp.is_dir():
            messagebox.showerror("Invalid folder", "Please select a valid image folder.")
            return

        tess = self.tess_var.get().strip()
        if not tess or not Path(tess).exists():
            messagebox.showerror("Tesseract not found", "Tesseract is installed, but this app cannot find tesseract.exe.\n\nClick Browse / Detect and select:\nC:\\Program Files\\Tesseract-OCR\\tesseract.exe")
            return
        pytesseract.pytesseract.tesseract_cmd = tess
        try:
            pytesseract.get_tesseract_version()
        except Exception as e:
            messagebox.showerror("Tesseract error", f"Cannot run Tesseract:\n{e}")
            return

        images = sorted([p for p in inp.iterdir() if p.suffix.lower() in SUPPORTED])
        if not images:
            messagebox.showwarning("No images", "No supported images were found in the selected folder.")
            return

        out.mkdir(parents=True, exist_ok=True)
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_var.set(0)
        self.log.delete("1.0", "end")
        threading.Thread(target=self._worker, args=(images, out), daemon=True).start()

    def stop(self):
        self.stop_event.set()
        self.status_var.set("Stopping...")
        self.log_msg("[INFO] Stop requested. Finishing current image...")

    def _preprocess(self, image):
        image = ImageOps.exif_transpose(image)
        image = image.convert("L")
        # Upscale for small screenshots/scans.
        if image.width < 1600:
            scale = 1600 / image.width
            image = image.resize((int(image.width*scale), int(image.height*scale)), Image.Resampling.LANCZOS)
        image = ImageOps.autocontrast(image)
        image = ImageEnhance.Sharpness(image).enhance(1.5)
        image = ImageEnhance.Contrast(image).enhance(1.25)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        return image

    def _ocr_image(self, path, lang):
        img = Image.open(path)
        if self.accuracy_var.get():
            img = self._preprocess(img)
        # psm 6 works well for screenshots/documents with blocks of text.
        return pytesseract.image_to_string(img, lang=lang, config="--oem 3 --psm 6")

    def _worker(self, images, out):
        lang = LANGUAGES[self.lang_var.get()]
        rows = []
        total = len(images)

        self.log_msg(f"[INFO] Found {total} image(s).")
        self.log_msg(f"[INFO] OCR language: {self.lang_var.get()}")
        try:
            installed = pytesseract.get_languages(config="")
            missing = [x for x in lang.split("+") if x not in installed]
            if missing:
                self.msg_queue.put(("error", "Missing Tesseract language data: " + ", ".join(missing) + "\n\nInstall the Bengali/Hindi language packs in Tesseract and try again."))
                return
        except Exception:
            pass

        for i, path in enumerate(images, 1):
            if self.stop_event.is_set():
                break
            self.log_msg(f"[INFO] Processing: {path.name}")
            try:
                text = self._ocr_image(path, lang)
                text = text.strip()
                rows.append({
                    "File Name": path.name,
                    "Extracted Text": text,
                    "Status": "Success"
                })
            except Exception as e:
                rows.append({
                    "File Name": path.name,
                    "Extracted Text": "",
                    "Status": f"Error: {e}"
                })
                self.log_msg(f"[ERROR] {path.name}: {e}")

            self.msg_queue.put(("progress", i, total))

        if rows:
            xlsx = out / "OCR_Output.xlsx"
            try:
                df = pd.DataFrame(rows)
                df.to_excel(xlsx, index=False, engine="openpyxl")
                # Also save a UTF-8 text file for easy backup/search.
                txt = out / "OCR_Output.txt"
                with txt.open("w", encoding="utf-8") as f:
                    for r in rows:
                        f.write(f"===== {r['File Name']} =====\n")
                        f.write(r["Extracted Text"])
                        f.write("\n\n")
                self.msg_queue.put(("done", str(xlsx), len(rows)))
            except Exception as e:
                self.msg_queue.put(("error", f"Could not save output: {e}"))
        else:
            self.msg_queue.put(("done", "", 0))

    def _poll_queue(self):
        try:
            while True:
                item = self.msg_queue.get_nowait()
                if item[0] == "log":
                    self.log.insert("end", item[1] + "\n")
                    self.log.see("end")
                elif item[0] == "progress":
                    _, i, total = item
                    pct = (i / total) * 100
                    self.progress_var.set(pct)
                    self.status_var.set(f"{i}/{total} images")
                elif item[0] == "done":
                    _, xlsx, count = item
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.progress_var.set(100 if count else 0)
                    self.status_var.set("Completed")
                    self.log_msg("[SUCCESS] OCR completed!")
                    if xlsx:
                        self.log_msg(f"[INFO] Excel saved to: {xlsx}")
                        messagebox.showinfo("OCR Complete", f"Processed {count} image(s).\n\nExcel saved to:\n{xlsx}")
                    else:
                        messagebox.showinfo("OCR", "No images were processed.")
                elif item[0] == "error":
                    self.start_btn.config(state="normal")
                    self.stop_btn.config(state="disabled")
                    self.status_var.set("Error")
                    messagebox.showerror("Error", item[1])
        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

if __name__ == "__main__":
    OCRApp().mainloop()
