import tkinter as tk
from tkinter import ttk, messagebox
from pynput import keyboard
import threading
import time
import json
from tkinter import filedialog
import queue

class AutoKeyPresser:
    def __init__(self, master):
        self.master = master
        self.master.title("Auto Key Presser")
        self.master.geometry("520x750")
        self.master.configure(bg="#f0f0f0")
        
        self.sequence = []
        self.recording = False
        self.playing = False
        self.paused = False
        self.listener = None
        self.hotkey_listener = None
        self.queue = queue.Queue()
        self.current_repeat = 0
        
        self.override_delay = tk.BooleanVar()
        self.override_ms = tk.IntVar(value=100)
        self.repeats = tk.IntVar(value=1)
        self.between_repeats = tk.IntVar(value=0)
        self.hotkey = keyboard.Key.f6
        
        self.create_widgets()
        
        self.bind_hotkey()
        self.validate_numeric_inputs()
        self.master.after(100, self.process_queue) 
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing) # Para evitar que se queden teclas presionadas al cerrar
    
    #?-- UI --#
    def create_widgets(self):
        style = ttk.Style()
        style.configure("Record.TButton", foreground="#e74c3c", background="#e74c3c", font=("Arial", 10, "bold"))
        style.configure("Play.TButton", foreground="#3498db", background="#3498db", font=("Arial", 10, "bold"))
        style.configure("TButton", font=("Arial", 10), padding=5)
        style.configure("Title.TLabel", font=("Arial", 12, "bold"), foreground="#2c3e50")
        
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        title = ttk.Label(main_frame, text="Auto Key Presser", style="Title.TLabel", font=("Arial", 16, "bold"))
        title.pack(pady=(0, 10))
        
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.record_btn = ttk.Button(btn_frame, text="◉ Record (F9)", command=self.toggle_record, width=15, style="Record.TButton")
        self.record_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.play_btn = ttk.Button(btn_frame, text="▶ Play (F6)", command=self.toggle_play, width=20, style="Play.TButton")
        self.play_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(btn_frame, text="Clear", command=self.clear_sequence, width=15)
        self.clear_btn.pack(side=tk.LEFT)
        
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Checkbutton(config_frame, text="Override Delays", variable=self.override_delay).pack(anchor=tk.W)

        delay_frame = ttk.Frame(config_frame)
        delay_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(delay_frame, text="Delay (ms):").pack(side=tk.LEFT)
        self.delay_entry = ttk.Entry(delay_frame, textvariable=self.override_ms, width=10)
        self.delay_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        rep_frame = ttk.Frame(config_frame)
        rep_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(rep_frame, text="Repetitions (0 = infinite):").pack(side=tk.LEFT)
        self.repeats_entry = ttk.Entry(rep_frame, textvariable=self.repeats, width=10)
        self.repeats_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        between_frame = ttk.Frame(config_frame)
        between_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(between_frame, text="Pause between reps (sec):").pack(side=tk.LEFT)
        self.between_entry = ttk.Entry(between_frame, textvariable=self.between_repeats, width=10)
        self.between_entry.pack(side=tk.LEFT, padx=(5, 0))
        
        hotkey_frame = ttk.LabelFrame(main_frame, text="Hotkeys", padding="10")
        hotkey_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(hotkey_frame, text="F6: Play/Pause\nF9: Record\nEsc: Stop", font=("Arial", 9)).pack()
        
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Arial", 10, "bold"), foreground="#e74c3c")
        status_label.pack(side=tk.LEFT)

        self.duration_var = tk.StringVar(value="Duration: 0.0 sec")
        duration_label = ttk.Label(status_frame, textvariable=self.duration_var, font=("Arial", 9, "bold"), foreground="#27ae60")
        duration_label.pack(side=tk.RIGHT)
        
        seq_frame = ttk.LabelFrame(main_frame, text="Recorded Sequence", padding="10")
        seq_frame.pack(fill=tk.BOTH, expand=True)
        
        io_frame = ttk.Frame(seq_frame)
        io_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(io_frame, text="Export", command=self.export_sequence).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(io_frame, text="Import", command=self.import_sequence).pack(side=tk.LEFT)

        scrollbar = ttk.Scrollbar(seq_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.sequence_text = tk.Text(seq_frame, height=10, width=50, yscrollcommand=scrollbar.set, state=tk.DISABLED)
        self.sequence_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.sequence_text.yview)
        
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_frame.pack(fill=tk.X, pady=(10, 5))
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='determinate', length=100)
        self.progress_bar.pack(fill=tk.X)
        
        self.bottom_status_var = tk.StringVar(value="")
        bottom_status = ttk.Label( main_frame, textvariable=self.bottom_status_var, font=("Arial", 8), foreground="#7f8c8d")
        bottom_status.pack(pady=(0, 10))
    
    #?-- CORE --#
    def process_queue(self):
        try:
            while not self.queue.empty():
                task = self.queue.get_nowait()
                task()
        except queue.Empty:
            pass
        self.master.after(100, self.process_queue)
    
    def update_progress_bar(self, value=None, mode=None, reset=False):
        def task():
            if reset:
                self.progress_bar.config(mode='determinate')
                self.progress_bar.stop()
                
                self.progress_bar['value'] = 0
                self.bottom_status_var.set("")
                return
                
            if mode:
                self.progress_bar.config(mode=mode)
                if mode == 'indeterminate':
                    self.progress_bar.start(10)
                else:
                    self.progress_bar.stop()
                    
            if value is not None:
                self.progress_bar['value'] = value
                
        self.queue.put(task)
    
    def update_bottom_status(self, repeats_left, time_left=None):
        def task():
            if repeats_left == "∞":
                text = f"Infinite repeats"
            else:
                text = f"Repeats left: {repeats_left}"
                
            if time_left is not None:
                text += f" | Next in: {time_left:.1f} sec"
                
            self.bottom_status_var.set(text)
            
        self.queue.put(task)
    
    def validate_numeric_inputs(self):
        vcmd = (self.master.register(self.is_numeric), '%P')
        self.delay_entry.config(validate='key', validatecommand=vcmd)
        self.repeats_entry.config(validate='key', validatecommand=vcmd)
        self.between_entry.config(validate='key', validatecommand=vcmd)
        
    def export_sequence(self):
        """This function exports the sequence to a JSON file"""
        if not self.sequence:
            messagebox.showwarning("Warning", "No sequence to export.")
            return

        file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Save Sequence")
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(self.sequence, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Success", f"Sequence exported to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save the sequence:\n{e}")

    def import_sequence(self):
        """Import sequence from a JSON file"""
        file_path = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON Files", "*.json")], title="Load Sequence")
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Validate format -> list of lists with 3 elements [str, str, int]
            if (isinstance(data, list) and
                all(isinstance(item, list) and len(item) == 3 and
                    item[0] in ("press", "release") and
                    isinstance(item[1], str) and
                    isinstance(item[2], int)
                    for item in data)):

                self.sequence = data
                self.update_sequence_display()
                self.update_duration_display()
                self.status_var.set(f"Sequence imported! ({len(self.sequence)} events)")
            else:
                messagebox.showerror("Error", "Invalid format in sequence file.")

        except json.JSONDecodeError:
            messagebox.showerror("Error", "File does not contain valid JSON.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not load sequence:\n{e}")

    def is_numeric(self, value):
        """Validate numeric input"""
        if value == "":
            return True
        try:
            int(value)
            return True
        except ValueError:
            return False
    
    def toggle_record(self):
        if not self.recording:
            self.start_record()
        else:
            self.stop_record()
            
    def on_closing(self):
        self.stop_play()
        self.release_all_keys()
        self.master.destroy()
    
    def start_record(self):
        if self.playing:
            messagebox.showwarning("Warning!", "Stop playback before recording")
            return
            
        self.sequence.clear()
        self.recording = True
        self.record_btn.config(text="⏹ Stop (F9)")
        self.status_var.set("Recording... Press F9 to stop")

        self.last_time = None
        self.listener = keyboard.Listener(on_press=self.on_press, 
                                        on_release=self.on_release)
        self.listener.start()
        
    def stop_record(self):
        self.recording = False
        if self.listener:
            self.listener.stop()
        self.record_btn.config(text="◉ Record (F9)")
        self.status_var.set(f"Recording stopped, ({len(self.sequence)} events)")
        self.update_sequence_display()
        self.update_duration_display()
    
    def on_press(self, key):
        if key == keyboard.Key.f9:
            self.stop_record()
            return
            
        now = time.time()
        delay = 0 if self.last_time is None else int((now - self.last_time) * 1000)
        self.sequence.append(("press", str(key), delay))
        self.last_time = now
        self.update_sequence_display()
    
    def on_release(self, key):
        if key == keyboard.Key.f9:
            return
            
        now = time.time()
        delay = 0 if self.last_time is None else int((now - self.last_time) * 1000)
        self.sequence.append(("release", str(key), delay))
        self.last_time = now
        self.update_sequence_display()
    
    def toggle_play(self):
        if not self.playing:
            self.start_play()
        else:
            self.stop_play()
    
    def start_play(self):
        if not self.sequence:
            messagebox.showwarning("Warning!", "No recorded sequence")
            return
            
        if self.recording:
            messagebox.showwarning("Warning!", "Stop recording before playing")
            return
            
        self.playing = True
        self.paused = False
        self.play_btn.config(text="⏸ Pause (F6)")
        self.status_var.set("Playing...")
        
        # Block inputs
        self.toggle_inputs(state=tk.DISABLED)

        # progress bar
        if self.repeats.get() == 0:  # Infinite
            self.update_progress_bar(mode='indeterminate')
            self.update_bottom_status("∞")
        else:
            self.update_progress_bar(mode='determinate')
            self.update_bottom_status(self.repeats.get())
        
        threading.Thread(target=self.play_sequence, daemon=True).start()
    
    def stop_play(self):
        self.playing = False
        self.play_btn.config(text="▶ Play (F6)")
        self.status_var.set("Playback stopped")
        self.toggle_inputs(state=tk.NORMAL)
        self.update_progress_bar(reset=True)
        self.release_all_keys()
    
    def play_sequence(self):
        kb = keyboard.Controller()
        self.current_repeat = 0
        total_repeats = self.repeats.get() if self.repeats.get() != 0 else float('inf')
        
        try:
            while self.playing and self.current_repeat < total_repeats:
                self.current_repeat += 1

                # Update first!
                if total_repeats == float('inf'):
                    repeats_left = "∞"
                else:
                    repeats_left = max(0, total_repeats - self.current_repeat)
                self.update_bottom_status(repeats_left)
                self.update_progress_bar(mode='indeterminate')
                
                for event_type, key_str, delay in self.sequence:
                    if not self.playing:
                        break
                        
                    # Parse key
                    try:
                        if key_str.startswith("Key."):
                            key = getattr(keyboard.Key, key_str.split(".")[1])
                        elif key_str.startswith("'") and key_str.endswith("'"):
                            key = keyboard.KeyCode.from_char(key_str[1:-1])
                        else:
                            key = keyboard.KeyCode.from_char(key_str)
                    except:
                        continue
                    
                    # Delay
                    if self.override_delay.get():
                        time.sleep(self.override_ms.get() / 1000)
                    else:
                        time.sleep(delay / 1000)

                    # Execute event
                    try:
                        if event_type == "press":
                            kb.press(key)
                        elif event_type == "release":
                            kb.release(key)
                    except:
                        pass

                # Update remaining repeats after completing the sequence
                if total_repeats == float('inf'):
                    repeats_left = "∞"
                else:
                    repeats_left = max(0, total_repeats - self.current_repeat)

                # Time between repeats
                if self.playing and self.current_repeat < total_repeats and self.between_repeats.get() > 0:
                    self.update_progress_bar(mode='determinate', value=0)
                    
                    wait_time = self.between_repeats.get()
                    step = 0.1
                    steps = int(wait_time / step)
                    
                    for i in range(steps):
                        if not self.playing:
                            break
                            
                        progress = ((i + 1) / steps) * 100
                        time_left = max(0, wait_time - (i * step))
                        
                        self.update_progress_bar(value=progress)
                        self.update_bottom_status(
                            "∞" if total_repeats == float('inf') else repeats_left,
                            time_left
                        )
                        time.sleep(step)
                        
        finally:
            self.release_all_keys()
        
        if self.playing:
            self.stop_play()
    
    def toggle_inputs(self, state):
        """Activate or deactivate input fields"""
        self.delay_entry.config(state=state)
        self.repeats_entry.config(state=state)
        self.between_entry.config(state=state)
        self.clear_btn.config(state=state)
    
    def clear_sequence(self):
        if self.playing:
            messagebox.showwarning("Warning", "Stop playback before clearing")
            return
            
        self.sequence.clear()
        self.update_sequence_display()
        self.update_duration_display()
        self.status_var.set("Sequence cleared")

    def update_sequence_display(self):
        self.sequence_text.config(state=tk.NORMAL)
        self.sequence_text.delete(1.0, tk.END)
        
        for i, (event_type, key, delay) in enumerate(self.sequence):
            self.sequence_text.insert(tk.END, f"{i+1:2d}. {event_type.upper():8} | {str(key):20} | {delay:4d}ms\n")
        
        self.sequence_text.config(state=tk.DISABLED)
    
    def update_duration_display(self):
        if not self.sequence:
            duration = 0.0
        else:
            duration = sum(delay for _, _, delay in self.sequence) / 1000

        self.duration_var.set(f"Duration: {duration:.1f} sec")

    def bind_hotkey(self):
        """To manage global hotkeys"""
        def on_hotkey(key):
            if key == keyboard.Key.f6:
                self.master.after(0, self.toggle_play)
            elif key == keyboard.Key.f9:
                if self.recording:
                    self.master.after(0, self.stop_record)
                else:
                    self.master.after(0, self.start_record)
            elif key == keyboard.Key.esc and self.playing:
                self.master.after(0, self.stop_play)
        
        self.hotkey_listener = keyboard.Listener(on_press=on_hotkey)
        self.hotkey_listener.start()
        
    def release_all_keys(self):
        """Release common keys to prevent them from being stuck"""
        kb = keyboard.Controller()
        keys_to_release = [
            keyboard.Key.shift,
            keyboard.Key.shift_r,
            keyboard.Key.ctrl,
            keyboard.Key.ctrl_r,
            keyboard.Key.alt,
            keyboard.Key.alt_r,
            keyboard.Key.space,
            keyboard.Key.enter,
            keyboard.Key.backspace,
            keyboard.Key.tab,
            keyboard.Key.esc,
        ]
        for key in keys_to_release:
            try:
                kb.release(key)
            except:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoKeyPresser(root)
    root.mainloop()