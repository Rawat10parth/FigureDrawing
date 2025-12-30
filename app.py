import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import os, random, json

SETTINGS_FILE = "settings.json"

BG = "#121212"
FG = "#EAEAEA"
ACCENT = "#EDEDED"
MUTED = "#9E9E9E"

class QuickPoseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("QuickPose")
        self.root.geometry("1000x700")
        self.root.configure(bg=BG)

        self.settings = self.load_settings()

        # ===== State =====
        self.images = []
        self.index = 0
        self.time_left = 0
        self.timer_id = None
        self.paused = False
        self.started = False
        self.fullscreen = False
        self.tk_img = None

        # ===== Canvas =====
        self.canvas = tk.Canvas(root, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda e: self.show())

        # ===== Overlay (Timer + Counter) =====
        overlay = tk.Frame(root, bg=BG)
        overlay.pack(fill="x", pady=4)

        self.timer_label = tk.Label(
            overlay,
            text=f"{self.settings['pose_time']}s",
            font=("Arial", 34, "bold"),
            fg=ACCENT,
            bg=BG
        )
        self.timer_label.pack(side="left", padx=20)

        self.counter_label = tk.Label(
            overlay,
            text="0 / 0",
            font=("Arial", 14),
            fg=MUTED,
            bg=BG
        )
        self.counter_label.pack(side="right", padx=20)

        # ===== Controls =====
        controls = tk.Frame(root, bg=BG)
        controls.pack(pady=10)

        self.big_btn(controls, "📁 Folder", self.load_folder).grid(row=0, column=0, padx=6)
        self.big_btn(controls, "⏮ Prev", self.prev).grid(row=0, column=1, padx=6)

        self.pause_btn = self.big_btn(
            controls, "⏸ Pause", self.toggle_pause, state="disabled"
        )
        self.pause_btn.grid(row=0, column=2, padx=6)

        self.big_btn(controls, "⏭ Next", self.next).grid(row=0, column=3, padx=6)

        # ===== Time + Start =====
        bottom = tk.Frame(root, bg=BG)
        bottom.pack(pady=5)

        tk.Label(bottom, text="Seconds:", fg=FG, bg=BG, font=("Arial", 14))\
            .grid(row=0, column=0)

        self.time_entry = tk.Entry(
            bottom, width=5, font=("Arial", 16), justify="center"
        )
        self.time_entry.insert(0, self.settings["pose_time"])
        self.time_entry.grid(row=0, column=1, padx=5)

        self.big_btn(bottom, "▶ Start", self.start).grid(row=0, column=2, padx=8)

        # ===== Load last folder (no auto start) =====
        if os.path.isdir(self.settings["last_folder"]):
            self.load_images(self.settings["last_folder"])

        # ===== Hotkeys =====
        root.bind("<space>", lambda e: self.toggle_pause())
        root.bind("<Return>", lambda e: self.start())
        root.bind("<Right>", lambda e: self.next())
        root.bind("<Left>", lambda e: self.prev())
        root.bind("f", lambda e: self.toggle_fullscreen())
        root.bind("<Escape>", lambda e: self.exit_fullscreen())

        root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ===== UI Helper =====
    def big_btn(self, parent, text, cmd, state="normal"):
        return tk.Button(
            parent, text=text, command=cmd,
            font=("Arial", 14, "bold"),
            bg="#1F1F1F", fg=FG,
            activebackground="#333",
            width=8, height=1,
            bd=0, state=state
        )

    # ===== Settings =====
    def load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        return {"pose_time": 60, "last_folder": ""}

    def save_settings(self):
        self.settings["pose_time"] = int(self.time_entry.get())
        with open(SETTINGS_FILE, "w") as f:
            json.dump(self.settings, f, indent=4)

    # ===== Folder Picker =====
    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.settings["last_folder"] = folder
        self.save_settings()
        self.load_images(folder)

    # ===== RECURSIVE IMAGE LOADING =====
    def load_images(self, folder):
        self.images = []

        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(("jpg", "jpeg", "png")):
                    self.images.append(os.path.join(root, file))

        if not self.images:
            return

        random.shuffle(self.images)
        self.index = 0
        self.started = False
        self.paused = False

        self.pause_btn.config(state="disabled", text="⏸ Pause")
        self.timer_label.config(text=f"{self.time_entry.get()}s")
        self.update_counter()
        self.show()

    # ===== Session =====
    def start(self):
        if not self.images:
            return
        self.started = True
        self.paused = False
        self.pause_btn.config(state="normal", text="⏸ Pause")
        self.reset_timer()
        self.update_counter()
        self.save_settings()

    # ===== Timer =====
    def reset_timer(self):
        self.cancel_timer()
        self.time_left = int(self.time_entry.get())
        self.update_timer()
        self.tick()

    def tick(self):
        if not self.started or self.paused:
            return
        if self.time_left <= 0:
            self.next()
            return
        self.time_left -= 1
        self.update_timer()
        self.timer_id = self.root.after(1000, self.tick)

    def update_timer(self):
        self.timer_label.config(text=f"{self.time_left}s")

    def cancel_timer(self):
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
            self.timer_id = None

    def toggle_pause(self):
        if not self.started:
            return
        self.paused = not self.paused
        if self.paused:
            self.cancel_timer()
            self.pause_btn.config(text="▶ Resume")
        else:
            self.pause_btn.config(text="⏸ Pause")
            self.tick()

    # ===== Image Rendering =====
    def show(self):
        if not self.images:
            return

        self.canvas.delete("all")

        img = Image.open(self.images[self.index])

        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw < 10 or ch < 10:
            return

        img_ratio = img.width / img.height
        canvas_ratio = cw / ch

        if img_ratio > canvas_ratio:
            new_w = cw
            new_h = int(cw / img_ratio)
        else:
            new_h = ch
            new_w = int(ch * img_ratio)

        img = img.resize((new_w, new_h), Image.LANCZOS)
        self.tk_img = ImageTk.PhotoImage(img)

        self.canvas.create_image(
            cw // 2, ch // 2,
            image=self.tk_img,
            anchor="center"
        )

    # ===== Counter =====
    def update_counter(self):
        total = len(self.images)
        current = self.index + 1 if total > 0 else 0
        self.counter_label.config(text=f"{current} / {total}")

    # ===== Navigation =====
    def next(self):
        if not self.started:
            return
        if self.index < len(self.images) - 1:
            self.index += 1
            self.show()
            self.reset_timer()
            self.update_counter()

    def prev(self):
        if not self.started:
            return
        if self.index > 0:
            self.index -= 1
            self.show()
            self.reset_timer()
            self.update_counter()

    # ===== Fullscreen =====
    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)

    def exit_fullscreen(self):
        self.fullscreen = False
        self.root.attributes("-fullscreen", False)

    # ===== Close =====
    def on_close(self):
        self.save_settings()
        self.root.destroy()

# ===== Run =====
if __name__ == "__main__":
    root = tk.Tk()
    QuickPoseApp(root)
    root.mainloop()
