import customtkinter as ctk
import tkinter as tk
import random
import time
import json
import os
import statistics
import math

# ============================================================
# SLIQTEST
# CPS + REACTION TEST + AUTO CLICKER DETECTION
# ============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DATA_FILE = "sliqtest_data.json"

BG = "#080B12"
SIDEBAR = "#0D111A"
CARD = "#121824"
HOVER = "#1B2638"

ACCENT = "#5865F2"
ACCENT_HOVER = "#4752C4"

GREEN = "#20D68A"
GREEN_HOVER = "#18B875"

RED = "#ED4245"
YELLOW = "#F5C542"

TEXT = "#FFFFFF"
MUTED = "#8994A8"


# ============================================================
# DEFAULT DATA
# ============================================================

DEFAULT_DATA = {
    "username": "Player",
    "best_cps": 0.0,
    "best_reaction": None,
    "cps_tests": [],
    "reaction_tests": []
}


# ============================================================
# DATA
# ============================================================

def load_data():

    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:

        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)

        for key, value in DEFAULT_DATA.items():

            if key not in loaded:

                if isinstance(value, list):
                    loaded[key] = []

                else:
                    loaded[key] = value

        return loaded

    except Exception as e:

        print("Load error:", e)

        return DEFAULT_DATA.copy()


data = load_data()


def save_data():

    try:

        with open(DATA_FILE, "w", encoding="utf-8") as f:

            json.dump(
                data,
                f,
                indent=4
            )

    except Exception as e:

        print("Save error:", e)


# ============================================================
# RANK
# ============================================================

def get_rank():

    cps = data.get("best_cps", 0)
    reaction = data.get("best_reaction")

    points = 0

    if cps >= 15:
        points += 5

    elif cps >= 12:
        points += 4

    elif cps >= 9:
        points += 3

    elif cps >= 6:
        points += 2

    elif cps >= 3:
        points += 1

    if reaction is not None:

        if reaction <= 150:
            points += 5

        elif reaction <= 200:
            points += 4

        elif reaction <= 250:
            points += 3

        elif reaction <= 300:
            points += 2

        elif reaction <= 400:
            points += 1

    if points >= 9:
        return "DIAMOND", "💎"

    if points >= 7:
        return "PLATINUM", "🏆"

    if points >= 5:
        return "GOLD", "🥇"

    if points >= 3:
        return "SILVER", "🥈"

    return "BRONZE", "🥉"


# ============================================================
# AUTO CLICKER DETECTION
# ============================================================

def detect_auto_clicker(click_times, duration):

    """
    Returns:
        suspicious: bool
        score: float
        reason: str

    The detector looks at the intervals between clicks.

    It does NOT simply ban high CPS.

    It looks for:
    - extremely consistent intervals
    - very low interval variation
    - long sequences with almost identical timing
    """

    if len(click_times) < 12:

        return False, 0.0, "Not enough clicks to analyze"

    intervals = []

    for i in range(1, len(click_times)):

        interval = click_times[i] - click_times[i - 1]

        if interval > 0:
            intervals.append(interval)

    if len(intervals) < 10:

        return False, 0.0, "Not enough intervals"


    # --------------------------------------------------------
    # Basic statistics
    # --------------------------------------------------------

    mean_interval = statistics.mean(intervals)

    if mean_interval <= 0:

        return True, 100.0, "Invalid click timing"


    try:

        stdev = statistics.stdev(intervals)

    except statistics.StatisticsError:

        stdev = 0


    coefficient_variation = stdev / mean_interval


    # --------------------------------------------------------
    # Count extremely similar intervals
    # --------------------------------------------------------

    similar_pairs = 0

    for i in range(1, len(intervals)):

        difference = abs(
            intervals[i] - intervals[i - 1]
        )

        tolerance = max(
            0.0025,
            mean_interval * 0.015
        )

        if difference <= tolerance:

            similar_pairs += 1


    similarity_ratio = (
        similar_pairs / max(1, len(intervals) - 1)
    )


    # --------------------------------------------------------
    # Quantized timing detection
    #
    # Some autoclickers generate intervals around exactly
    # the same millisecond value.
    # --------------------------------------------------------

    rounded_intervals = [
        round(interval * 1000)
        for interval in intervals
    ]

    frequency = {}

    for value in rounded_intervals:

        frequency[value] = frequency.get(value, 0) + 1

    most_common_count = max(
        frequency.values()
    )

    dominant_ratio = (
        most_common_count / len(rounded_intervals)
    )


    # --------------------------------------------------------
    # Very low variation
    # --------------------------------------------------------

    extremely_consistent = (
        coefficient_variation < 0.015
    )

    highly_consistent = (
        coefficient_variation < 0.025
    )


    # --------------------------------------------------------
    # Score
    # --------------------------------------------------------

    score = 0.0
    reasons = []


    if extremely_consistent:

        score += 55

        reasons.append(
            "extremely consistent click intervals"
        )

    elif highly_consistent:

        score += 30

        reasons.append(
            "very consistent click intervals"
        )


    if similarity_ratio >= 0.90:

        score += 30

        reasons.append(
            "almost identical intervals"
        )

    elif similarity_ratio >= 0.80:

        score += 20

        reasons.append(
            "high interval similarity"
        )


    if dominant_ratio >= 0.90:

        score += 30

        reasons.append(
            "same interval repeated unusually often"
        )

    elif dominant_ratio >= 0.80:

        score += 20

        reasons.append(
            "dominant interval pattern"
        )


    # --------------------------------------------------------
    # Extremely high CPS + very consistent timing
    #
    # High CPS alone is NOT enough.
    # --------------------------------------------------------

    cps = len(click_times) / duration

    if cps >= 15 and coefficient_variation < 0.03:

        score += 20

        reasons.append(
            "high CPS with unusually stable timing"
        )


    if cps >= 20 and coefficient_variation < 0.04:

        score += 15


    # --------------------------------------------------------
    # Final decision
    # --------------------------------------------------------

    suspicious = score >= 70

    if not reasons:

        reason = "normal timing variation"

    else:

        reason = ", ".join(reasons)


    return suspicious, min(score, 100), reason


# ============================================================
# MAIN APP
# ============================================================

class SliqTest(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title("SliqTest")
        self.geometry("1200x760")
        self.minsize(1000, 650)

        self.configure(
            fg_color=BG
        )


        # ----------------------------------------------------
        # CPS
        # ----------------------------------------------------

        self.cps_running = False
        self.cps_finished = False

        self.cps_clicks = 0
        self.cps_start = 0
        self.cps_end = 0

        self.cps_click_times = []
        self.cps_auto_click_detected = False
        self.cps_mode_locked = False

        self.cps_click_times = []


        # ----------------------------------------------------
        # Reaction
        # ----------------------------------------------------

        self.reaction_state = "ready"

        self.reaction_start_time = 0

        self.reaction_timer = None


        # ----------------------------------------------------
        # UI
        # ----------------------------------------------------

        self.create_sidebar()


        self.content = ctk.CTkFrame(
            self,
            fg_color=BG,
            corner_radius=0
        )

        self.content.pack(
            side="right",
            fill="both",
            expand=True
        )


        self.show_dashboard()


    # ========================================================
    # SIDEBAR
    # ========================================================

    def create_sidebar(self):

        self.sidebar = ctk.CTkFrame(
            self,
            width=230,
            fg_color=SIDEBAR,
            corner_radius=0
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)


        ctk.CTkLabel(
            self.sidebar,
            text="SLIQTEST",
            font=ctk.CTkFont(
                size=28,
                weight="bold"
            )
        ).pack(
            pady=(35, 2)
        )


        ctk.CTkLabel(
            self.sidebar,
            text="TEST YOUR LIMITS",
            font=ctk.CTkFont(size=11),
            text_color=MUTED
        ).pack(
            pady=(0, 35)
        )


        self.nav(
            "🏠   Dashboard",
            self.show_dashboard
        )

        self.nav(
            "🖱️   CPS Test",
            self.show_cps
        )

        self.nav(
            "⚡   Reaction Test",
            self.show_reaction
        )

        self.nav(
            "📊   Statistics",
            self.show_statistics
        )

        self.nav(
            "🏆   Leaderboard",
            self.show_leaderboard
        )

        self.nav(
            "👤   Profile",
            self.show_profile
        )


        self.sidebar_bottom = ctk.CTkFrame(
            self.sidebar,
            fg_color="transparent"
        )

        self.sidebar_bottom.pack(
            side="bottom",
            pady=25
        )


        self.update_sidebar_rank()


    def nav(self, text, command):

        button = ctk.CTkButton(
            self.sidebar,
            text=text,
            command=command,
            height=46,
            corner_radius=10,
            fg_color="transparent",
            hover_color=HOVER,
            anchor="w",
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        )

        button.pack(
            fill="x",
            padx=14,
            pady=4
        )


    def update_sidebar_rank(self):

        for widget in self.sidebar_bottom.winfo_children():

            widget.destroy()


        rank, emoji = get_rank()


        ctk.CTkLabel(
            self.sidebar_bottom,
            text=f"{emoji} {rank}",
            font=ctk.CTkFont(
                size=16,
                weight="bold"
            ),
            text_color=YELLOW
        ).pack()


        ctk.CTkLabel(
            self.sidebar_bottom,
            text=data.get(
                "username",
                "Player"
            ),
            text_color=MUTED
        ).pack(
            pady=(4, 0)
        )


    # ========================================================
    # HELPERS
    # ========================================================

    def clear(self):

        for widget in self.content.winfo_children():

            widget.destroy()


    def page_title(self, title, subtitle):

        ctk.CTkLabel(
            self.content,
            text=title,
            font=ctk.CTkFont(
                size=32,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=40,
            pady=(35, 2)
        )


        ctk.CTkLabel(
            self.content,
            text=subtitle,
            font=ctk.CTkFont(size=14),
            text_color=MUTED
        ).pack(
            anchor="w",
            padx=40,
            pady=(0, 25)
        )


    def make_card(self, parent):

        return ctk.CTkFrame(
            parent,
            fg_color=CARD,
            corner_radius=18
        )


    # ========================================================
    # DASHBOARD
    # ========================================================

    def show_dashboard(self):

        self.clear()


        self.page_title(
            "Welcome back 👋",
            f"Ready to test yourself, {data.get('username', 'Player')}?"
        )


        area = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        area.pack(
            fill="both",
            expand=True,
            padx=40
        )


        stats = ctk.CTkFrame(
            area,
            fg_color="transparent"
        )

        stats.pack(
            fill="x"
        )


        self.dashboard_stat(
            stats,
            "🖱️",
            "BEST CPS",
            f"{data.get('best_cps', 0):.2f}"
        )


        best_reaction = data.get(
            "best_reaction"
        )


        self.dashboard_stat(
            stats,
            "⚡",
            "BEST REACTION",
            f"{best_reaction} ms"
            if best_reaction is not None
            else "--"
        )


        rank, emoji = get_rank()


        self.dashboard_stat(
            stats,
            emoji,
            "RANK",
            rank
        )


        tests = ctk.CTkFrame(
            area,
            fg_color="transparent"
        )

        tests.pack(
            fill="x",
            pady=25
        )


        self.test_card(
            tests,
            "🖱️",
            "CPS TEST",
            "How fast can you click?",
            ACCENT,
            ACCENT_HOVER,
            self.show_cps
        )


        self.test_card(
            tests,
            "⚡",
            "REACTION TEST",
            "How fast can you react?",
            GREEN,
            GREEN_HOVER,
            self.show_reaction
        )


        tip = self.make_card(area)

        tip.pack(
            fill="x",
            pady=(0, 20)
        )


        ctk.CTkLabel(
            tip,
            text="💡  PRO TIP",
            font=ctk.CTkFont(
                size=15,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(18, 5)
        )


        ctk.CTkLabel(
            tip,
            text="Take multiple tests and try to beat your personal best.",
            text_color=MUTED
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 18)
        )


    def dashboard_stat(
        self,
        parent,
        icon,
        name,
        value
    ):

        card = self.make_card(parent)

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )


        ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=25)
        ).pack(
            pady=(18, 0)
        )


        ctk.CTkLabel(
            card,
            text=name,
            text_color=MUTED
        ).pack()


        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            )
        ).pack(
            pady=(2, 18)
        )


    def test_card(
        self,
        parent,
        icon,
        title,
        description,
        color,
        hover,
        command
    ):

        card = self.make_card(parent)

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )


        ctk.CTkLabel(
            card,
            text=icon,
            font=ctk.CTkFont(size=42)
        ).pack(
            pady=(28, 5)
        )


        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(
                size=21,
                weight="bold"
            )
        ).pack()


        ctk.CTkLabel(
            card,
            text=description,
            text_color=MUTED
        ).pack(
            pady=6
        )


        ctk.CTkButton(
            card,
            text="START TEST",
            height=45,
            corner_radius=10,
            fg_color=color,
            hover_color=hover,
            command=command
        ).pack(
            fill="x",
            padx=35,
            pady=(12, 28)
        )


    # ========================================================
    # CPS TEST
    # ========================================================

    def show_cps(self):

        self.clear()


        self.page_title(
            "CPS Test 🖱️",
            "Click as fast as possible."
        )


        area = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        area.pack(
            fill="both",
            expand=True,
            padx=40
        )


        settings = self.make_card(area)

        settings.pack(
            fill="x",
            pady=(0, 15)
        )


        ctk.CTkLabel(
            settings,
            text="TEST DURATION",
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            ),
            text_color=MUTED
        ).pack(
            side="left",
            padx=(20, 10),
            pady=15
        )


        self.cps_duration = tk.StringVar(
            value="10"
        )


        ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=[
                "5",
                "10",
                "15",
                "30"
            ],
            width=100
        ).pack(
            side="left",
            pady=10
        )


        panel = self.make_card(area)

        panel.pack(
            fill="both",
            expand=True
        )


        self.cps_status = ctk.CTkLabel(
            panel,
            text="READY?",
            font=ctk.CTkFont(
                size=35,
                weight="bold"
            )
        )

        self.cps_status.pack(
            pady=(30, 0)
        )


        self.cps_value = ctk.CTkLabel(
            panel,
            text="0",
            font=ctk.CTkFont(
                size=65,
                weight="bold"
            )
        )

        self.cps_value.pack()


        self.cps_timer_label = ctk.CTkLabel(
            panel,
            text="Click to start",
            text_color=MUTED,
            font=ctk.CTkFont(size=15)
        )

        self.cps_timer_label.pack()


        self.cps_button = ctk.CTkButton(
            panel,
            text="CLICK!",
            width=280,
            height=125,
            corner_radius=22,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(
                size=28,
                weight="bold"
            ),
            command=None
        )

        self.cps_button.pack(
            pady=20
        )


        ctk.CTkButton(
            panel,
            text="RESET",
            width=110,
            height=35,
            fg_color="#202938",
            hover_color=HOVER,
            command=self.reset_cps
        ).pack(
            pady=(0, 20)
        )


        self.cps_running = False
        self.cps_finished = False
        self.cps_clicks = 0
        self.cps_click_times = []


    def cps_mouse_click(self, event=None):
        self.cps_click()

    def cps_click(self):

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

    def update_cps(self):

        if not self.cps_running:

            return


        remaining = (
            self.cps_end
            - time.perf_counter()
        )


        if remaining <= 0:

            self.finish_cps()

            return


        self.cps_timer_label.configure(
            text=f"{remaining:.2f} seconds remaining"
        )


        self.after(
            10,
            self.update_cps
        )


    def finish_cps(self):

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

    def reset_cps(self):

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

    # ========================================================
    # REACTION TEST
    # ========================================================

    def show_reaction(self):

        self.clear()


        self.page_title(
            "Reaction Test ⚡",
            "Wait for green. Then click immediately."
        )


        area = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        area.pack(
            fill="both",
            expand=True,
            padx=40
        )


        settings = self.make_card(area)

        settings.pack(
            fill="x",
            pady=(0, 15)
        )


        ctk.CTkLabel(
            settings,
            text="DIFFICULTY",
            text_color=MUTED,
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            )
        ).pack(
            side="left",
            padx=(20, 10),
            pady=15
        )


        self.reaction_difficulty = tk.StringVar(
            value="Normal"
        )


        ctk.CTkOptionMenu(
            settings,
            variable=self.reaction_difficulty,
            values=[
                "Easy",
                "Normal",
                "Hard",
                "Extreme"
            ],
            width=120
        ).pack(
            side="left"
        )


        self.reaction_button = ctk.CTkButton(
            area,
            text="PRESS START",
            corner_radius=22,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(
                size=30,
                weight="bold"
            ),
            command=None
        )

        self.reaction_button.pack(
            fill="both",
            expand=True
        )

        # Direct mouse event - no CTkButton command cooldown
        self.reaction_button.bind("<Button-1>", self.reaction_mouse_click)


        self.reaction_info = ctk.CTkLabel(
            area,
            text="",
            text_color=MUTED,
            font=ctk.CTkFont(size=15)
        )

        self.reaction_info.pack(
            pady=15
        )


        self.reaction_state = "ready"


    def reaction_mouse_click(self, event=None):
        self.reaction_click()

    def reaction_click(self):

        if self.reaction_state == "waiting":

            if self.reaction_timer:

                try:

                    self.after_cancel(
                        self.reaction_timer
                    )

                except Exception:

                    pass


            self.reaction_timer = None

            self.reaction_state = "ready"


            self.reaction_button.configure(
                text="TOO EARLY!",
                fg_color=RED,
                hover_color=RED
            )


            self.reaction_info.configure(
                text="You clicked before the signal. Try again."
            )


            return


        if self.reaction_state == "go":

            elapsed = (
                time.perf_counter()
                - self.reaction_start_time
            )


            milliseconds = round(
                elapsed * 1000
            )


            data["reaction_tests"].append(
                milliseconds
            )


            best = data.get(
                "best_reaction"
            )


            if (
                best is None
                or milliseconds < best
            ):

                data["best_reaction"] = milliseconds


            save_data()


            self.reaction_state = "ready"


            self.reaction_button.configure(
                text=f"{milliseconds} MS",
                fg_color=GREEN,
                hover_color=GREEN_HOVER
            )


            self.reaction_info.configure(
                text="Nice! Press again for another test."
            )


            self.update_sidebar_rank()


            return


        difficulty = (
            self.reaction_difficulty.get()
        )


        if difficulty == "Easy":

            delay = random.uniform(
                2.0,
                5.0
            )

        elif difficulty == "Normal":

            delay = random.uniform(
                1.5,
                4.0
            )

        elif difficulty == "Hard":

            delay = random.uniform(
                1.0,
                3.0
            )

        else:

            delay = random.uniform(
                0.5,
                2.0
            )


        self.reaction_state = "waiting"


        self.reaction_button.configure(
            text="WAIT...",
            fg_color=RED,
            hover_color=RED
        )


        self.reaction_info.configure(
            text="Don't click yet!"
        )


        self.reaction_timer = self.after(
            int(delay * 1000),
            self.reaction_go
        )


    def reaction_go(self):

        self.reaction_timer = None

        self.reaction_state = "go"


        self.reaction_start_time = (
            time.perf_counter()
        )


        self.reaction_button.configure(
            text="CLICK NOW!",
            fg_color=GREEN,
            hover_color=GREEN_HOVER
        )


        self.reaction_info.configure(
            text="GO!"
        )


    # ========================================================
    # STATISTICS
    # ========================================================

    def show_statistics(self):

        self.clear()


        self.page_title(
            "Statistics 📊",
            "See how your performance is improving."
        )


        area = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        area.pack(
            fill="both",
            expand=True,
            padx=40
        )


        cps = data.get(
            "cps_tests",
            []
        )


        reaction = data.get(
            "reaction_tests",
            []
        )


        cps_card = self.make_card(area)

        cps_card.pack(
            fill="x",
            pady=(0, 15)
        )


        ctk.CTkLabel(
            cps_card,
            text="🖱️ CPS",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 8)
        )


        if cps:

            average = (
                sum(cps)
                / len(cps)
            )


            text = (
                f"Tests: {len(cps)}    "
                f"Average: {average:.2f} CPS    "
                f"Best: {max(cps):.2f} CPS"
            )

        else:

            text = (
                "No CPS tests completed yet."
            )


        ctk.CTkLabel(
            cps_card,
            text=text,
            text_color=MUTED
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 20)
        )


        reaction_card = self.make_card(area)

        reaction_card.pack(
            fill="x",
            pady=15
        )


        ctk.CTkLabel(
            reaction_card,
            text="⚡ REACTION",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 8)
        )


        if reaction:

            average = (
                sum(reaction)
                / len(reaction)
            )


            text = (
                f"Tests: {len(reaction)}    "
                f"Average: {average:.0f} ms    "
                f"Best: {min(reaction)} ms"
            )

        else:

            text = (
                "No reaction tests completed yet."
            )


        ctk.CTkLabel(
            reaction_card,
            text=text,
            text_color=MUTED
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 20)
        )


        rank, emoji = get_rank()


        rank_card = self.make_card(area)

        rank_card.pack(
            fill="x",
            pady=15
        )


        ctk.CTkLabel(
            rank_card,
            text=f"{emoji}  {rank}",
            font=ctk.CTkFont(
                size=32,
                weight="bold"
            ),
            text_color=YELLOW
        ).pack(
            pady=(22, 5)
        )


        ctk.CTkLabel(
            rank_card,
            text="Keep testing to rank up.",
            text_color=MUTED
        ).pack(
            pady=(0, 22)
        )


    # ========================================================
    # LEADERBOARD
    # ========================================================

    def show_leaderboard(self):

        self.clear()


        self.page_title(
            "Leaderboard 🏆",
            "Your top 3 recorded performances."
        )


        area = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        area.pack(
            fill="both",
            expand=True,
            padx=40
        )


        self.leaderboard_card(
            area,
            "🖱️  TOP 3 CPS",
            data.get(
                "cps_tests",
                []
            ),
            "CPS",
            True
        )


        self.leaderboard_card(
            area,
            "⚡  TOP 3 REACTION",
            data.get(
                "reaction_tests",
                []
            ),
            "ms",
            False
        )


    def leaderboard_card(
        self,
        parent,
        title,
        values,
        unit,
        higher_is_better
    ):

        card = self.make_card(parent)

        card.pack(
            fill="x",
            pady=10
        )


        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 12)
        )


        if not values:

            ctk.CTkLabel(
                card,
                text="No results yet.",
                text_color=MUTED
            ).pack(
                anchor="w",
                padx=25,
                pady=(0, 20)
            )

            return


        sorted_values = sorted(
            values,
            reverse=higher_is_better
        )


        top_values = sorted_values[:3]


        medals = [
            "🥇",
            "🥈",
            "🥉"
        ]


        for index, value in enumerate(
            top_values
        ):

            row = ctk.CTkFrame(
                card,
                fg_color=(
                    HOVER
                    if index == 0
                    else "transparent"
                ),
                corner_radius=10
            )


            row.pack(
                fill="x",
                padx=15,
                pady=4
            )


            if unit == "CPS":

                result = (
                    f"{value:.2f} CPS"
                )

            else:

                result = (
                    f"{value} ms"
                )


            ctk.CTkLabel(
                row,
                text=medals[index],
                font=ctk.CTkFont(
                    size=23
                )
            ).pack(
                side="left",
                padx=(15, 12),
                pady=10
            )


            ctk.CTkLabel(
                row,
                text=data.get(
                    "username",
                    "Player"
                ),
                font=ctk.CTkFont(
                    size=14,
                    weight="bold"
                )
            ).pack(
                side="left"
            )


            ctk.CTkLabel(
                row,
                text=result,
                font=ctk.CTkFont(
                    size=16,
                    weight="bold"
                )
            ).pack(
                side="right",
                padx=15
            )


        ctk.CTkLabel(
            card,
            text="Automatically updated after every valid result.",
            text_color=MUTED,
            font=ctk.CTkFont(
                size=11
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(8, 18)
        )


    # ========================================================
    # PROFILE
    # ========================================================

    def show_profile(self):

        self.clear()


        self.page_title(
            "Profile 👤",
            "Customize your SliqTest profile."
        )


        area = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        area.pack(
            fill="both",
            expand=True,
            padx=40
        )


        card = self.make_card(area)

        card.pack(
            fill="x"
        )


        ctk.CTkLabel(
            card,
            text="USERNAME",
            text_color=MUTED,
            font=ctk.CTkFont(
                size=13,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 6)
        )


        self.username_entry = ctk.CTkEntry(
            card,
            height=45,
            corner_radius=10
        )


        self.username_entry.insert(
            0,
            data.get(
                "username",
                "Player"
            )
        )


        self.username_entry.pack(
            fill="x",
            padx=25
        )


        ctk.CTkButton(
            card,
            text="SAVE PROFILE",
            height=45,
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            command=self.save_profile
        ).pack(
            fill="x",
            padx=25,
            pady=25
        )


    def save_profile(self):

        username = (
            self.username_entry
            .get()
            .strip()
        )


        if not username:

            username = "Player"


        # Limit username length

        username = username[:24]


        data["username"] = username


        save_data()


        self.update_sidebar_rank()


        self.show_profile()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    print("Starting SliqTest...")


    app = SliqTest()


    print(
        "SliqTest started successfully."
    )


    app.mainloop()