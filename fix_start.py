from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# ============================================================
# REMOVE GLOBAL CPS MOUSE HANDLER
# ============================================================

s = s.replace(
'''        self.bind_all("<ButtonPress-1>", self.global_mouse_click, add="+")
        
''',
''
)

# Remove global_mouse_click function if present
start = s.find("    def global_mouse_click(self, event):")

if start != -1:
    end = s.find("    # ========================================================", start)

    if end != -1:
        s = s[:start] + s[end:]

# ============================================================
# CPS BUTTON
# ============================================================

# Make sure CPS button does NOT use CTkButton command
s = s.replace(
'''            command=self.cps_click
''',
'''            command=None
''',
1
)

# Remove previous CPS bindings
s = s.replace(
'''        self.cps_button.bind("<Button-1>", self.cps_mouse_click)
''',
''
)

s = s.replace(
'''        self.cps_button.bind("<ButtonPress-1>", self.cps_mouse_click)
''',
''
)

# ============================================================
# ADD DIRECT CPS BUTTON BINDING
# ============================================================

needle = '''        self.cps_button.pack(pady=20)
'''

replacement = '''        self.cps_button.pack(pady=20)

        # Direct mouse click.
        # This handles BOTH the first click and every
        # following click without a CTkButton command.
        self.cps_button.bind(
            "<ButtonPress-1>",
            self.cps_mouse_click
        )
'''

if needle not in s:
    raise Exception("CPS button pack section not found.")

s = s.replace(
    needle,
    replacement,
    1
)

# ============================================================
# CPS MOUSE CLICK FUNCTION
# ============================================================

# Remove existing cps_mouse_click if present
start = s.find("    def cps_mouse_click(self, event=None):")

if start != -1:
    end = s.find("    def cps_click(self):", start)

    if end != -1:
        s = s[:start] + s[end:]

# Add fresh handler
marker = '''    def cps_click(self):
'''

mouse_handler = '''    def cps_mouse_click(self, event=None):

        # IMPORTANT:
        # There is NO cooldown here.
        # Every mouse press is immediately passed to cps_click.

        self.cps_click()

        return "break"


'''

if marker not in s:
    raise Exception("cps_click function not found.")

s = s.replace(
    marker,
    mouse_handler + marker,
    1
)

# ============================================================
# CPS CLICK FUNCTION
# ============================================================

start = s.find("    def cps_click(self):")
end = s.find("    def update_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("Could not find cps_click.")

new_cps = '''    def cps_click(self):

        if self.cps_finished:
            return

        now = time.perf_counter()

        # ====================================================
        # FIRST CLICK = START
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

            # LOCK DURATION DURING TEST
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

            self.update_idletasks()

            self.update_cps()

            return

        # ====================================================
        # EVERY FOLLOWING CLICK
        # ====================================================

        self.cps_clicks += 1

        self.cps_click_times.append(now)

        # IMMEDIATELY UPDATE NUMBER
        self.cps_value.configure(
            text=str(self.cps_clicks)
        )

        self.update_idletasks()

        # ====================================================
        # AUTO CLICKER DETECTION
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

                # Extremely regular timing
                # is suspicious.
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
# MAKE SURE CPS VARIABLES EXIST
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
# CPS DURATION MENU
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

# ============================================================
# WRITE FILE
# ============================================================

p.write_text(s, encoding="utf-8")

print("CPS START + CLICK SYSTEM FIXED")
