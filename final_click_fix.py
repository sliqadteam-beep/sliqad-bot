from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# ============================================================
# 1. REMOVE OLD CPS MOUSE SYSTEMS
# ============================================================

import re

s = re.sub(
    r'\s*self\.cps_button\.bind_all\([^\n]*\)\n',
    '',
    s
)

s = re.sub(
    r'\s*self\.cps_button\.bind\([^\n]*\n\s*[^)]*\)\n',
    '',
    s
)

# ============================================================
# 2. ADD GLOBAL CLICK HANDLER AFTER APP INITIALIZATION
# ============================================================

needle = '''        self.show_dashboard()
'''

replacement = '''        # Direct global mouse handler.
        # This completely bypasses CTkButton click handling.
        self.bind_all("<ButtonPress-1>", self.global_mouse_click, add="+")
        
        self.show_dashboard()
'''

if "self.bind_all(\"<ButtonPress-1>\"" not in s:
    s = s.replace(needle, replacement, 1)

# ============================================================
# 3. ADD GLOBAL MOUSE FUNCTION
# ============================================================

marker = '''    # ========================================================
    # SIDEBAR
    # ========================================================
'''

global_function = '''    def global_mouse_click(self, event):

        # CPS TEST
        if getattr(self, "cps_running", False):

            # Only count clicks while the CPS test is active.
            self.cps_click()

        return None

'''

if "def global_mouse_click(self, event):" not in s:
    s = s.replace(
        marker,
        global_function + marker,
        1
    )

# ============================================================
# 4. CPS CLICK FUNCTION
# ============================================================

start = s.find("    def cps_click(self):")
end = s.find("    def update_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("CPS CLICK FUNCTION NOT FOUND")

new_cps = '''    def cps_click(self):

        if self.cps_finished:
            return

        now = time.perf_counter()

        # ====================================================
        # FIRST CLICK
        # ====================================================

        if not self.cps_running:

            self.cps_running = True
            self.cps_finished = False

            self.cps_clicks = 1

            self.cps_start = now

            duration = int(self.cps_duration.get())

            self.cps_end = now + duration

            self.cps_click_times = [now]
            self.cps_auto_click_detected = False

            # LOCK THE MODE
            if hasattr(self, "cps_duration_menu"):
                self.cps_duration_menu.configure(
                    state="disabled"
                )

            self.cps_status.configure(
                text="CLICK!",
                text_color=GREEN
            )

            self.cps_value.configure(
                text="1"
            )

            self.cps_timer_label.configure(
                text=f"{duration:.2f} seconds remaining"
            )

            self.update_cps()

            return

        # ====================================================
        # EVERY CLICK IS REGISTERED
        # ====================================================

        self.cps_clicks += 1

        self.cps_click_times.append(now)

        self.cps_value.configure(
            text=str(self.cps_clicks)
        )

        # Force Tkinter to immediately redraw the number.
        self.update_idletasks()

        # ====================================================
        # AUTO CLICKER DETECTION
        # ====================================================

        if len(self.cps_click_times) >= 20:

            recent = self.cps_click_times[-20:]

            intervals = []

            for i in range(1, len(recent)):
                intervals.append(
                    recent[i] - recent[i - 1]
                )

            average = sum(intervals) / len(intervals)

            if average > 0:

                deviation = (
                    sum(
                        (x - average) ** 2
                        for x in intervals
                    )
                    / len(intervals)
                ) ** 0.5

                variation = deviation / average

                # Very consistent clicking.
                if (
                    0.02 <= average <= 1.0
                    and variation < 0.04
                ):

                    self.cps_auto_click_detected = True

                    self.cps_status.configure(
                        text="AUTO CLICKER DETECTED",
                        text_color=RED
                    )

                    self.cps_timer_label.configure(
                        text="Suspicious clicking detected."
                    )

'''

s = s[:start] + new_cps + s[end:]

# ============================================================
# 5. CPS FINISH
# ============================================================

start = s.find("    def finish_cps(self):")
end = s.find("    def reset_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("FINISH CPS FUNCTION NOT FOUND")

new_finish = '''    def finish_cps(self):

        self.cps_running = False
        self.cps_finished = True

        # Unlock mode after test.
        if hasattr(self, "cps_duration_menu"):
            self.cps_duration_menu.configure(
                state="normal"
            )

        duration = int(self.cps_duration.get())

        # ====================================================
        # AUTO CLICKER
        # ====================================================

        if self.cps_auto_click_detected:

            self.cps_status.configure(
                text="AUTO CLICKER DETECTED",
                text_color=RED
            )

            self.cps_value.configure(
                text="INVALID"
            )

            self.cps_timer_label.configure(
                text="Result was not saved."
            )

            return

        # ====================================================
        # NORMAL RESULT
        # ====================================================

        cps = round(
            self.cps_clicks / duration,
            2
        )

        data["cps_tests"].append(cps)

        if cps > data["best_cps"]:
            data["best_cps"] = cps

        save_data()

        self.cps_status.configure(
            text="FINISHED!",
            text_color=YELLOW
        )

        self.cps_value.configure(
            text=f"{cps:.2f}"
        )

        self.cps_timer_label.configure(
            text=f"{self.cps_clicks} clicks in {duration} seconds"
        )

        self.update_sidebar_rank()

'''

s = s[:start] + new_finish + s[end:]

# ============================================================
# 6. CPS RESET
# ============================================================

start = s.find("    def reset_cps(self):")
end = s.find("    # ========================================================", start)

if start == -1 or end == -1:
    raise Exception("RESET CPS FUNCTION NOT FOUND")

new_reset = '''    def reset_cps(self):

        self.cps_running = False
        self.cps_finished = False

        self.cps_clicks = 0

        self.cps_click_times = []

        self.cps_auto_click_detected = False

        if hasattr(self, "cps_duration_menu"):
            self.cps_duration_menu.configure(
                state="normal"
            )

        self.cps_status.configure(
            text="READY?",
            text_color=TEXT
        )

        self.cps_value.configure(
            text="0"
        )

        self.cps_timer_label.configure(
            text="Click START below"
        )

'''

s = s[:start] + new_reset + s[end:]

# ============================================================
# 7. ENSURE CPS VARIABLES EXIST
# ============================================================

if "self.cps_click_times = []" not in s:

    s = s.replace(
        "        self.cps_end = 0",
        '''        self.cps_end = 0
        self.cps_click_times = []
        self.cps_auto_click_detected = False''',
        1
    )

# ============================================================
# 8. ENSURE DURATION MENU CAN BE LOCKED
# ============================================================

old_menu = '''        ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=["5", "10", "15", "30"],
            width=100
        ).pack(
            side="left",
            pady=10
        )
'''

new_menu = '''        self.cps_duration_menu = ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=["5", "10", "15", "30"],
            width=100
        )

        self.cps_duration_menu.pack(
            side="left",
            pady=10
        )
'''

s = s.replace(old_menu, new_menu)

p.write_text(s, encoding="utf-8")

print("GLOBAL CLICK SYSTEM INSTALLED")
