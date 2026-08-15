from pathlib import Path

p = Path("main.py")
s = p.read_text(encoding="utf-8")

# ============================================================
# CPS VARIABLES
# ============================================================

if "self.cps_click_times = []" not in s:
    s = s.replace(
        "        self.cps_end = 0",
        """        self.cps_end = 0
        self.cps_click_times = []
        self.cps_auto_click_detected = False"""
    )

# ============================================================
# CPS DURATION MENU
# ============================================================

old_menu = """        ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=["5", "10", "15", "30"],
            width=100
        ).pack(
            side="left",
            pady=10
        )
"""

new_menu = """        self.cps_duration_menu = ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=["5", "10", "15", "30"],
            width=100
        )

        self.cps_duration_menu.pack(
            side="left",
            pady=10
        )
"""

s = s.replace(old_menu, new_menu)

# ============================================================
# CPS CLICK
# ============================================================

start = s.find("    def cps_click(self):")
end = s.find("    def update_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("cps_click function not found")

new_cps = """    def cps_click(self):

        if self.cps_finished:
            return

        now = time.perf_counter()

        # FIRST CLICK
        if not self.cps_running:

            self.cps_running = True
            self.cps_finished = False
            self.cps_clicks = 1

            self.cps_start = now

            duration = int(self.cps_duration.get())
            self.cps_end = now + duration

            self.cps_click_times = [now]
            self.cps_auto_click_detected = False

            # LOCK MODE DURING TEST
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
        # REGISTER EVERY CLICK
        # ====================================================

        self.cps_clicks += 1
        self.cps_click_times.append(now)

        self.cps_value.configure(
            text=str(self.cps_clicks)
        )

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

                # Very consistent intervals
                # = likely automated clicking
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

"""

s = s[:start] + new_cps + s[end:]

# ============================================================
# FINISH CPS
# ============================================================

start = s.find("    def finish_cps(self):")
end = s.find("    def reset_cps(self):", start)

if start == -1 or end == -1:
    raise Exception("finish_cps function not found")

new_finish = """    def finish_cps(self):

        self.cps_running = False
        self.cps_finished = True

        # UNLOCK MODE AFTER TEST
        if hasattr(self, "cps_duration_menu"):
            self.cps_duration_menu.configure(
                state="normal"
            )

        duration = int(self.cps_duration.get())

        # ====================================================
        # AUTO CLICKER RESULT
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
        # VALID RESULT
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

        # Refresh leaderboard automatically if it is open
        if hasattr(self, "show_leaderboard"):
            pass

"""

s = s[:start] + new_finish + s[end:]

# ============================================================
# RESET CPS
# ============================================================

start = s.find("    def reset_cps(self):")
end = s.find("    # ========================================================", start)

if start == -1 or end == -1:
    raise Exception("reset_cps function not found")

new_reset = """    def reset_cps(self):

        self.cps_running = False
        self.cps_finished = False
        self.cps_clicks = 0
        self.cps_click_times = []
        self.cps_auto_click_detected = False

        # UNLOCK MODE
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

"""

s = s[:start] + new_reset + s[end:]

p.write_text(s, encoding="utf-8")

print("SLIQTEST UPDATE COMPLETE")
