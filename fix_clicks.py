from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# ============================================================
# CPS BUTTON - remove command based clicking
# ============================================================

s = s.replace(
    '            command=self.cps_click',
    '            command=None'
)

# Remove old CPS bindings if they exist
s = s.replace(
'''        self.cps_button.bind("<Button-1>", self.cps_mouse_click)
''',
''
)

s = s.replace(
'''        self.cps_button.bind("<Button-1>", self.cps_click)
''',
''
)

# Add direct mouse binding after CPS button creation/pack
needle = '''        self.cps_button.pack(pady=20)
'''

replacement = '''        self.cps_button.pack(pady=20)

        # Direct mouse event.
        # This bypasses CTkButton command handling.
        self.cps_button.bind(
            "<Button-1>",
            self.cps_mouse_click
        )
'''

s = s.replace(needle, replacement, 1)

# ============================================================
# ADD CPS MOUSE CLICK FUNCTION
# ============================================================

marker = '''    def cps_click(self):
'''

if marker not in s:
    raise Exception("cps_click not found")

mouse_function = '''    def cps_mouse_click(self, event=None):

        # Direct mouse click handler.
        # There is intentionally NO cooldown here.

        self.cps_click()

        return "break"


'''

s = s.replace(
    marker,
    mouse_function + marker,
    1
)

# ============================================================
# REPLACE CPS CLICK FUNCTION
# ============================================================

start = s.find("    def cps_click(self):")
end = s.find("    def update_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("Could not find CPS click section.")

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

            # LOCK DURATION
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
        # EVERY CLICK
        # ====================================================

        self.cps_clicks += 1

        self.cps_click_times.append(now)

        # Update display immediately
        self.cps_value.configure(
            text=str(self.cps_clicks)
        )

        # ====================================================
        # AUTO CLICK DETECTION
        # ====================================================

        if len(self.cps_click_times) >= 20:

            recent = self.cps_click_times[-20:]

            intervals = [
                recent[i] - recent[i - 1]
                for i in range(1, len(recent))
            ]

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

                if (
                    0.02 <= average <= 1.0
                    and variation < 0.035
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
# MAKE SURE VARIABLES EXIST
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
# REMOVE ANY REACTION DIRECT BINDING WE DON'T WANT
# ============================================================

s = s.replace(
'''        self.reaction_button.bind("<Button-1>", self.reaction_mouse_click)
''',
''
)

# ============================================================
# WRITE
# ============================================================

p.write_text(s, encoding="utf-8")

print("DIRECT CLICK SYSTEM INSTALLED")
