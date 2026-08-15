from pathlib import Path
import re

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# ============================================================
# CPS VARIABLES
# ============================================================

s = re.sub(
    r'        self\.cps_clicks = 0\s*\n        self\.cps_start = 0\s*\n        self\.cps_end = 0',
    '''        self.cps_clicks = 0
        self.cps_start = 0
        self.cps_end = 0

        self.cps_click_times = []
        self.cps_auto_click_detected = False
        self.cps_mode_locked = False''',
    s,
    count=1
)

# ============================================================
# CPS OPTION MENU
# ============================================================

old_menu = '''        ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=["5", "10", "15", "30"],
            width=100
        ).pack(
            side="left",
            pady=10
        )'''

new_menu = '''        self.cps_duration_menu = ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=["5", "10", "15", "30"],
            width=100
        )

        self.cps_duration_menu.pack(
            side="left",
            pady=10
        )'''

s = s.replace(old_menu, new_menu)

# ============================================================
# CPS BUTTON
# ============================================================

old_button = '''        self.cps_button = ctk.CTkButton(
            panel,
            text="CLICK!",
            width=280,
            height=125,
            corner_radius=22,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=28, weight="bold"),
            command=self.cps_click
        )
        self.cps_button.pack(pady=20)'''

new_button = '''        self.cps_button = ctk.CTkButton(
            panel,
            text="CLICK!",
            width=280,
            height=125,
            corner_radius=22,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(size=28, weight="bold")
        )

        self.cps_button.pack(pady=20)

        # Direct mouse press detection.
        # This avoids any perceived button-command delay.
        self.cps_button.bind(
            "<ButtonPress-1>",
            self.cps_mouse_press
        )'''

s = s.replace(old_button, new_button)

# ============================================================
# CPS INITIAL RESET
# ============================================================

s = re.sub(
    r'        self\.cps_running = False\s*\n        self\.cps_finished = False\s*\n        self\.cps_clicks = 0\s*\n\s*    def cps_click\(self\):',
    '''        self.cps_running = False
        self.cps_finished = False
        self.cps_clicks = 0
        self.cps_click_times = []
        self.cps_auto_click_detected = False
        self.cps_mode_locked = False

    def cps_mouse_press(self, event=None):
        self.cps_click()

    def cps_click(self):''',
    s,
    count=1
)

# ============================================================
# CPS CLICK FUNCTION
# ============================================================

start = s.index("    def cps_click(self):")
end = s.index("    def update_cps(self):", start)

new_click = '''    def cps_click(self):

        now = time.perf_counter()

        # ----------------------------------------------------
        # START
        # ----------------------------------------------------

        if not self.cps_running:

            if self.cps_finished:
                return

            self.cps_running = True
            self.cps_finished = False
            self.cps_auto_click_detected = False

            self.cps_clicks = 1
            self.cps_click_times = [now]

            self.cps_start = now

            duration = int(self.cps_duration.get())
            self.cps_end = now + duration

            # HARD LOCK
            self.cps_mode_locked = True

            try:
                self.cps_duration_menu.configure(
                    state="disabled"
                )
            except Exception:
                pass

            self.cps_status.configure(
                text="CLICK!",
                text_color=GREEN
            )

            self.cps_value.configure(
                text="1"
            )

            self.update_cps()
            return

        # ----------------------------------------------------
        # HARD LOCK CHECK
        # ----------------------------------------------------

        if self.cps_mode_locked:
            pass

        # ----------------------------------------------------
        # REGISTER EVERY CLICK
        # ----------------------------------------------------

        self.cps_clicks += 1
        self.cps_click_times.append(now)

        self.cps_value.configure(
            text=str(self.cps_clicks)
        )

        # ----------------------------------------------------
        # AUTO CLICKER DETECTION
        # ----------------------------------------------------

        if len(self.cps_click_times) >= 16:

            recent = self.cps_click_times[-16:]

            intervals = []

            for i in range(1, len(recent)):
                delta = recent[i] - recent[i - 1]

                if delta > 0:
                    intervals.append(delta)

            if len(intervals) >= 12:

                average = sum(intervals) / len(intervals)

                if average > 0:

                    # Standard deviation
                    variance = sum(
                        (x - average) ** 2
                        for x in intervals
                    ) / len(intervals)

                    deviation = variance ** 0.5

                    coefficient = deviation / average

                    # How many intervals are extremely close
                    # to the average?
                    close_count = sum(
                        1
                        for x in intervals
                        if abs(x - average)
                        <= max(0.0025, average * 0.035)
                    )

                    close_ratio = (
                        close_count / len(intervals)
                    )

                    # Detect highly regular automated clicking.
                    #
                    # This intentionally requires BOTH:
                    # 1. very low timing variation
                    # 2. most intervals nearly identical
                    #
                    # This prevents normal human clicking from
                    # being rejected too easily.

                    if (
                        coefficient < 0.045
                        and close_ratio >= 0.90
                        and average >= 0.035
                        and average <= 0.50
                    ):

                        self.cps_auto_click_detected = True

                        self.cps_status.configure(
                            text="AUTO CLICKER DETECTED",
                            text_color=RED
                        )

                        self.cps_timer_label.configure(
                            text="Automated clicking detected."
                        )

'''

s = s[:start] + new_click + s[end:]

# ============================================================
# FINISH CPS
# ============================================================

start = s.index("    def finish_cps(self):")
end = s.index("    def reset_cps(self):", start)

new_finish = '''    def finish_cps(self):

        self.cps_running = False
        self.cps_finished = True
        self.cps_mode_locked = False

        # Unlock mode selector
        try:
            self.cps_duration_menu.configure(
                state="normal"
            )
        except Exception:
            pass

        duration = int(self.cps_duration.get())

        cps = round(
            self.cps_clicks / duration,
            2
        )

        # ----------------------------------------------------
        # INVALID AUTO CLICKER RESULT
        # ----------------------------------------------------

        if self.cps_auto_click_detected:

            self.cps_status.configure(
                text="AUTO CLICKER DETECTED",
                text_color=RED
            )

            self.cps_value.configure(
                text="INVALID"
            )

            self.cps_timer_label.configure(
                text=(
                    f"{self.cps_clicks} clicks - "
                    "result was NOT saved"
                )
            )

            return

        # ----------------------------------------------------
        # VALID RESULT
        # ----------------------------------------------------

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
            text=(
                f"{self.cps_clicks} clicks "
                f"in {duration} seconds"
            )
        )

        self.update_sidebar_rank()

'''

s = s[:start] + new_finish + s[end:]

# ============================================================
# RESET CPS
# ============================================================

start = s.index("    def reset_cps(self):")
end = s.index("    # ========================================================", start)

new_reset = '''    def reset_cps(self):

        self.cps_running = False
        self.cps_finished = False
        self.cps_mode_locked = False

        self.cps_clicks = 0
        self.cps_click_times = []
        self.cps_auto_click_detected = False

        # Unlock mode selector
        try:
            self.cps_duration_menu.configure(
                state="normal"
            )
        except Exception:
            pass

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
# SAVE
# ============================================================

p.write_text(s, encoding="utf-8")

print("")
print("==========================================")
print(" SLIQTEST UPDATE COMPLETE")
print("==========================================")
print("")
print("CPS mode lock: ENABLED")
print("Direct click detection: ENABLED")
print("Auto-click detection: ENABLED")
print("5 / 10 / 15 / 30 seconds: ENABLED")
print("Click cooldown: REMOVED")
print("")
