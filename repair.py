from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# ------------------------------------------------------------
# Remove broken direct-event wrappers if present
# ------------------------------------------------------------

s = s.replace(
'''    def cps_mouse_click(self, event=None):
        self.cps_click()

''',
''''
)

s = s.replace(
'''    def reaction_mouse_click(self, event=None):
        self.reaction_click()

''',
''''
)

# ------------------------------------------------------------
# CPS BUTTON
# ------------------------------------------------------------

s = s.replace(
'''            command=None
''',
'''            command=self.cps_click
''',
1
)

# Remove direct CPS binding
s = s.replace(
'''        # Direct mouse event - no CTkButton command cooldown
        self.cps_button.bind("<Button-1>", self.cps_mouse_click)
''',
''''
)

# ------------------------------------------------------------
# REACTION BUTTON
# ------------------------------------------------------------

s = s.replace(
'''            command=None
''',
'''            command=self.reaction_click
''',
1
)

# Remove direct reaction binding
s = s.replace(
'''        # Direct mouse event - no CTkButton command cooldown
        self.reaction_button.bind("<Button-1>", self.reaction_mouse_click)
''',
''''
)

# ------------------------------------------------------------
# CPS CLICK FUNCTION
# ------------------------------------------------------------

start = s.find("    def cps_click(self):")
end = s.find("    def update_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("Could not find cps_click function.")

new_cps = '''    def cps_click(self):

        if self.cps_finished:
            return

        # First click starts the test
        if not self.cps_running:

            self.cps_running = True
            self.cps_finished = False

            self.cps_clicks = 1

            now = time.perf_counter()

            self.cps_start = now

            duration = int(self.cps_duration.get())

            self.cps_end = now + duration

            self.cps_click_times = [now]
            self.cps_auto_click_detected = False

            # Lock duration during the test
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

            self.update_cps()

            return

        # Every additional click is registered immediately
        now = time.perf_counter()

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
                interval = recent[i] - recent[i - 1]
                intervals.append(interval)

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

                # Very regular timing = suspicious
                if (
                    0.02 <= average <= 1.0
                    and variation < 0.025
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

# ------------------------------------------------------------
# CPS FINISH FUNCTION
# ------------------------------------------------------------

start = s.find("    def finish_cps(self):")
end = s.find("    def reset_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("Could not find finish_cps function.")

new_finish = '''    def finish_cps(self):

        self.cps_running = False
        self.cps_finished = True

        # Unlock duration after test
        if hasattr(self, "cps_duration_menu"):
            self.cps_duration_menu.configure(
                state="normal"
            )

        duration = int(self.cps_duration.get())

        # Invalid result if auto-clicker detected
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

# ------------------------------------------------------------
# CPS RESET
# ------------------------------------------------------------

start = s.find("    def reset_cps(self):")
end = s.find("    # ========================================================", start)

if start == -1 or end == -1:
    raise Exception("Could not find reset_cps function.")

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

# ------------------------------------------------------------
# Make sure CPS variables exist
# ------------------------------------------------------------

needle = '''        self.cps_end = 0
'''

if needle in s and "self.cps_click_times = []" not in s:
    s = s.replace(
        needle,
        needle +
        '''        self.cps_click_times = []
        self.cps_auto_click_detected = False
''',
        1
    )

p.write_text(s, encoding="utf-8")

print("CLICK SYSTEM REPAIRED")
