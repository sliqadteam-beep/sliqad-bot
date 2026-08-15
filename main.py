import customtkinter as ctk
import tkinter as tk
import random
import time
import json
import os
import webbrowser
import urllib.request
import urllib.error
import requests
import statistics

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

DATA_FILE = "sliqtest_data.json"

SERVER_URL = "https://sliqtest-server.onrender.com"

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


DEFAULT_DATA = {
    "username": "Player",
    "best_cps": 0.0,
    "best_reaction": None,
    "cps_tests": [],
    "reaction_tests": []
}


def load_data():
    if not os.path.exists(DATA_FILE):
        return DEFAULT_DATA.copy()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        for key, value in DEFAULT_DATA.items():
            if key not in data:
                data[key] = value

        return data

    except Exception:
        return DEFAULT_DATA.copy()


data = load_data()


def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print("Save error:", e)


def send_online_result(test_type, value):
    """Send a completed result to the SliqTest server."""
    try:
        payload = {
            "username": data.get("username", "Player"),
            "type": test_type,
            "value": value
        }

        request = urllib.request.Request(
            SERVER_URL + "/api/result",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status == 200

    except Exception as e:
        print("Online result error:", e)
        return False


def get_online_leaderboard():
    """Get leaderboard data from the SliqTest server."""
    try:
        request = urllib.request.Request(
            SERVER_URL + "/api/leaderboard",
            headers={
                "Accept": "application/json"
            }
        )

        with urllib.request.urlopen(request, timeout=8) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw)

            if isinstance(result, dict):
                return result

            return {}

    except Exception as e:
        print("Online leaderboard error:", e)
        return {}


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
        return "PLATINUM", ""
    if points >= 5:
        return "GOLD", "1."
    if points >= 3:
        return "SILVER", "2."

    return "BRONZE", "3."


def send_result_to_server(test_type, value):
    """Send a valid result to the online SliqTest server."""

    try:
        if test_type == "cps":
            response = requests.post(
                f"{SERVER_URL}/api/cps",
                json={
                    "username": data.get("username", "Player"),
                    "cps": value
                },
                timeout=8
            )

        elif test_type == "reaction":
            response = requests.post(
                f"{SERVER_URL}/api/reaction",
                json={
                    "username": data.get("username", "Player"),
                    "reaction_ms": value
                },
                timeout=8
            )

        else:
            return False

        return response.ok

    except Exception as e:
        print("Server connection error:", e)
        return False


class SliqTest(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("SliqTest")
        self.geometry("1200x760")
        self.minsize(1000, 650)
        self.configure(fg_color=BG)

        # CPS
        self.cps_running = False
        self.cps_finished = False
        self.cps_clicks = 0
        self.cps_start = 0
        self.cps_end = 0
        self.cps_click_times = []
        self.cps_auto_click_detected = False
        self.cps_timer_job = None

        # Reaction
        self.reaction_state = "ready"
        self.reaction_start_time = 0
        self.reaction_timer = None

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
            font=ctk.CTkFont(size=28, weight="bold")
        ).pack(pady=(35, 2))

        ctk.CTkLabel(
            self.sidebar,
            text="TEST YOUR LIMITS",
            font=ctk.CTkFont(size=11),
            text_color=MUTED
        ).pack(pady=(0, 35))

        self.nav("Dashboard", self.show_dashboard)
        self.nav("CPS Test", self.show_cps)
        self.nav("Reaction Test", self.show_reaction)
        self.nav("Statistics", self.show_statistics)
        self.nav("Leaderboard", self.show_leaderboard)
        self.nav("Profile", self.show_profile)

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

        ctk.CTkButton(
            self.sidebar,
            text=text,
            command=command,
            height=46,
            corner_radius=10,
            fg_color="transparent",
            hover_color=HOVER,
            anchor="w",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(
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
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=YELLOW
        ).pack()

        ctk.CTkLabel(
            self.sidebar_bottom,
            text=data["username"],
            text_color=MUTED
        ).pack(pady=(4, 0))

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
            font=ctk.CTkFont(size=32, weight="bold")
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
            "Welcome back",
            f"Ready to test yourself, {data['username']}?"
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

        stats.pack(fill="x")

        self.dashboard_stat(
            stats,
            "BEST CPS",
            f"{data['best_cps']:.2f}"
        )

        reaction = data["best_reaction"]

        self.dashboard_stat(
            stats,
            "BEST REACTION",
            f"{reaction} ms" if reaction else "--"
        )

        rank, _ = get_rank()

        self.dashboard_stat(
            stats,
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
            "CPS TEST",
            "Click as fast as possible.",
            ACCENT,
            ACCENT_HOVER,
            self.show_cps
        )

        self.test_card(
            tests,
            "REACTION TEST",
            "React as quickly as possible.",
            GREEN,
            GREEN_HOVER,
            self.show_reaction
        )

    def dashboard_stat(self, parent, name, value):

        card = self.make_card(parent)

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        ctk.CTkLabel(
            card,
            text=name,
            text_color=MUTED
        ).pack(pady=(20, 4))

        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=(0, 20))

    def test_card(
        self,
        parent,
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
            text=title,
            font=ctk.CTkFont(size=21, weight="bold")
        ).pack(pady=(30, 5))

        ctk.CTkLabel(
            card,
            text=description,
            text_color=MUTED
        ).pack(pady=6)

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
            pady=(15, 30)
        )

    # ========================================================
    # CPS TEST
    # ========================================================

    def show_cps(self):

        self.clear()

        self.page_title(
            "CPS Test",
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
            text_color=MUTED,
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(
            side="left",
            padx=(20, 10),
            pady=15
        )

        self.cps_duration = tk.StringVar(value="10")

        self.cps_duration_menu = ctk.CTkOptionMenu(
            settings,
            variable=self.cps_duration,
            values=["5", "10", "15", "30"],
            width=100
        )

        self.cps_duration_menu.pack(
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
            text="READY",
            font=ctk.CTkFont(size=35, weight="bold")
        )

        self.cps_status.pack(
            pady=(30, 0)
        )

        self.cps_value = ctk.CTkLabel(
            panel,
            text="0",
            font=ctk.CTkFont(size=65, weight="bold")
        )

        self.cps_value.pack()

        self.cps_timer_label = ctk.CTkLabel(
            panel,
            text="Click the button to start",
            text_color=MUTED,
            font=ctk.CTkFont(size=15)
        )

        self.cps_timer_label.pack()

        # ====================================================
        # CUSTOMTKINTER BUTTON
        # ====================================================

        self.cps_button = ctk.CTkButton(
            panel,
            text="CLICK!",
            width=280,
            height=110,
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
            pady=25
        )

        # Direct mouse event.
        # This bypasses the CTkButton command cooldown.
        self.cps_button.bind(
            "<Button-1>",
            self.cps_mouse_click,
            add="+"
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
        self.cps_auto_click_detected = False

    def cps_mouse_click(self, event=None):

        if self.cps_finished:
            return "break"

        # ====================================================
        # FIRST CLICK
        # ====================================================

        if not self.cps_running:

            now = time.perf_counter()

            self.cps_running = True
            self.cps_clicks = 1

            self.cps_start = now

            duration = int(
                self.cps_duration.get()
            )

            self.cps_end = (
                now + duration
            )

            self.cps_click_times = [now]
            self.cps_auto_click_detected = False

            # LOCK MODE
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

            self.cps_button.configure(
                text="CLICK!",
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER
            )

            self.update_cps()

            return "break"

        # ====================================================
        # ADDITIONAL CLICKS
        # ====================================================

        now = time.perf_counter()

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

            for i in range(
                1,
                len(recent)
            ):

                intervals.append(
                    recent[i]
                    - recent[i - 1]
                )

            if intervals:

                average = (
                    sum(intervals)
                    / len(intervals)
                )

                if average > 0:

                    deviation = (
                        statistics.pstdev(
                            intervals
                        )
                    )

                    variation = (
                        deviation
                        / average
                    )

                    # Very consistent timing
                    if (
                        0.015 <= average <= 1.0
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

        return "break"

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

        self.cps_timer_job = self.after(
            20,
            self.update_cps
        )

    def finish_cps(self):

        if not self.cps_running:
            return

        self.cps_running = False
        self.cps_finished = True

        if self.cps_timer_job:

            try:
                self.after_cancel(
                    self.cps_timer_job
                )
            except Exception:
                pass

            self.cps_timer_job = None

        self.cps_duration_menu.configure(
            state="normal"
        )

        duration = int(
            self.cps_duration.get()
        )

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
        # NORMAL RESULT
        # ====================================================

        cps = round(
            self.cps_clicks / duration,
            2
        )

        data["cps_tests"].append(
            cps
        )

        if cps > data["best_cps"]:

            data["best_cps"] = cps

        save_data()

        # Send result to online SliqTest server
        online_ok = send_result_to_server("cps", cps)

        self.cps_status.configure(
            text="FINISHED",
            text_color=YELLOW
        )

        self.cps_value.configure(
            text=f"{cps:.2f}"
        )

        self.cps_timer_label.configure(
            text=f"{self.cps_clicks} clicks in {duration} seconds"
        )

        self.update_sidebar_rank()

    def reset_cps(self):

        if self.cps_timer_job:

            try:
                self.after_cancel(
                    self.cps_timer_job
                )
            except Exception:
                pass

            self.cps_timer_job = None

        self.cps_running = False
        self.cps_finished = False
        self.cps_clicks = 0
        self.cps_click_times = []
        self.cps_auto_click_detected = False

        if hasattr(
            self,
            "cps_duration_menu"
        ):

            self.cps_duration_menu.configure(
                state="normal"
            )

        if hasattr(
            self,
            "cps_status"
        ):

            self.cps_status.configure(
                text="READY",
                text_color=TEXT
            )

            self.cps_value.configure(
                text="0"
            )

            self.cps_timer_label.configure(
                text="Click the button to start"
            )

            self.cps_button.configure(
                text="CLICK!",
                fg_color=ACCENT,
                hover_color=ACCENT_HOVER
            )

    # ========================================================
    # REACTION TEST
    # ========================================================

    def show_reaction(self):

        self.clear()

        self.page_title(
            "Reaction Test",
            "Wait for green, then click immediately."
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

        self.reaction_difficulty_menu = ctk.CTkOptionMenu(
            settings,
            variable=self.reaction_difficulty,
            values=[
                "Easy",
                "Normal",
                "Hard",
                "Extreme"
            ],
            width=120
        )

        self.reaction_difficulty_menu.pack(
            side="left"
        )

        self.reaction_button = ctk.CTkButton(
            area,
            text="PRESS START",
            height=250,
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
            fill="x",
            expand=False
        )

        self.reaction_button.bind(
            "<Button-1>",
            self.reaction_mouse_click,
            add="+"
        )

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

            self.reaction_difficulty_menu.configure(
                state="normal"
            )

            self.reaction_button.configure(
                text="TOO EARLY!",
                fg_color=RED,
                hover_color=RED
            )

            self.reaction_info.configure(
                text="You clicked before the signal. Try again."
            )

            return "break"

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

            if (
                data["best_reaction"] is None
                or milliseconds
                < data["best_reaction"]
            ):

                data["best_reaction"] = milliseconds

            save_data()

            # Send result to online SliqTest server
            online_ok = send_result_to_server(
                "reaction",
                milliseconds
            )

            self.reaction_state = "ready"

            self.reaction_difficulty_menu.configure(
                state="normal"
            )

            self.reaction_button.configure(
                text=f"{milliseconds} MS",
                fg_color=GREEN,
                hover_color=GREEN_HOVER
            )

            self.reaction_info.configure(
                text="Nice! Click again for another test."
            )

            self.update_sidebar_rank()

            return "break"

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

        self.reaction_difficulty_menu.configure(
            state="disabled"
        )

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

        return "break"

    def reaction_go(self):

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
            "Statistics",
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

        cps = data["cps_tests"]
        reaction = data["reaction_tests"]

        cps_card = self.make_card(area)

        cps_card.pack(
            fill="x",
            pady=(0, 15)
        )

        ctk.CTkLabel(
            cps_card,
            text="CPS",
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
                sum(cps) / len(cps)
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
            text="REACTION",
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

    # ========================================================
    # LEADERBOARD
    # ========================================================

    # ========================================================
    # LEADERBOARD
    # ========================================================

    def show_leaderboard(self):

        self.clear()

        self.page_title(
            "Leaderboard ??",
            "Your best recorded performances."
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

        # -------------------------------------------------
        # Online leaderboard container
        # -------------------------------------------------

        online_card = self.make_card(area)

        online_card.pack(
            fill="x",
            pady=10
        )

        ctk.CTkLabel(
            online_card,
            text="?? ONLINE LEADERBOARD",
            font=ctk.CTkFont(
                size=22,
                weight="bold"
            )
        ).pack(
            anchor="w",
            padx=25,
            pady=(20, 4)
        )

        self.online_status = ctk.CTkLabel(
            online_card,
            text="Loading online leaderboard...",
            text_color=MUTED,
            font=ctk.CTkFont(size=13)
        )

        self.online_status.pack(
            anchor="w",
            padx=25,
            pady=(0, 10)
        )

        self.online_cps_frame = ctk.CTkFrame(
            online_card,
            fg_color="transparent"
        )

        self.online_cps_frame.pack(
            fill="x",
            padx=15
        )

        self.online_reaction_frame = ctk.CTkFrame(
            online_card,
            fg_color="transparent"
        )

        self.online_reaction_frame.pack(
            fill="x",
            padx=15
        )

        self.online_last_update = ctk.CTkLabel(
            online_card,
            text="",
            text_color=MUTED,
            font=ctk.CTkFont(size=11)
        )

        self.online_last_update.pack(
            anchor="w",
            padx=25,
            pady=(8, 2)
        )

        ctk.CTkLabel(
            online_card,
            text="Results can take up to 60 seconds.",
            text_color=MUTED,
            font=ctk.CTkFont(size=11)
        ).pack(
            anchor="w",
            padx=25,
            pady=(0, 18)
        )

        # -------------------------------------------------
        # Online website button
        # -------------------------------------------------

        online_row = ctk.CTkFrame(
            area,
            fg_color="transparent"
        )

        online_row.pack(
            pady=(8, 10)
        )

        ctk.CTkLabel(
            online_row,
            text="See the full online leaderboard:",
            text_color=MUTED,
            font=ctk.CTkFont(size=13)
        ).pack(
            side="left",
            padx=(0, 10)
        )

        ctk.CTkButton(
            online_row,
            text="View Online Leaderboard ?",
            width=210,
            height=34,
            corner_radius=8,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=ctk.CTkFont(
                size=12,
                weight="bold"
            ),
            command=lambda: webbrowser.open(
                "https://sliqadteam-beep.github.io/sliqad-bot/"
            )
        ).pack(
            side="left"
        )

        # -------------------------------------------------
        # Local leaderboard
        # -------------------------------------------------

        ctk.CTkLabel(
            area,
            text="YOUR LOCAL RESULTS",
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            )
        ).pack(
            anchor="w",
            pady=(8, 0)
        )

        self.leaderboard_card(
            area,
            "??? TOP 3 CPS",
            data.get("cps_tests", []),
            "CPS",
            True
        )

        self.leaderboard_card(
            area,
            "? TOP 3 REACTION",
            data.get("reaction_tests", []),
            "ms",
            False
        )

        # Load online data
        self.load_online_leaderboard()

    def load_online_leaderboard(self):

        def worker():

            result = get_online_leaderboard()

            try:
                self.after(
                    0,
                    lambda: self.display_online_leaderboard(result)
                )
            except Exception:
                pass

        import threading

        threading.Thread(
            target=worker,
            daemon=True
        ).start()

    def display_online_leaderboard(self, result):

        try:

            # Clear old online entries
            for widget in self.online_cps_frame.winfo_children():
                widget.destroy()

            for widget in self.online_reaction_frame.winfo_children():
                widget.destroy()

            if not isinstance(result, dict):
                self.online_status.configure(
                    text="Server unavailable. Showing the last available data.",
                    text_color=YELLOW
                )
                return

            cps = result.get("cps", [])
            reaction = result.get("reaction", [])

            if not isinstance(cps, list):
                cps = []

            if not isinstance(reaction, list):
                reaction = []

            # ---------------------------------------------
            # CPS
            # ---------------------------------------------

            ctk.CTkLabel(
                self.online_cps_frame,
                text="??? TOP 3 CPS",
                font=ctk.CTkFont(
                    size=16,
                    weight="bold"
                )
            ).pack(
                anchor="w",
                padx=10,
                pady=(5, 4)
            )

            medals = ["??", "??", "??"]

            if cps:

                for index, item in enumerate(cps[:3]):

                    username = item.get(
                        "username",
                        "Player"
                    )

                    value = item.get(
                        "value",
                        0
                    )

                    row = ctk.CTkFrame(
                        self.online_cps_frame,
                        fg_color=HOVER if index == 0 else "transparent",
                        corner_radius=8
                    )

                    row.pack(
                        fill="x",
                        pady=2
                    )

                    ctk.CTkLabel(
                        row,
                        text=medals[index],
                        font=ctk.CTkFont(size=20)
                    ).pack(
                        side="left",
                        padx=(10, 10),
                        pady=7
                    )

                    ctk.CTkLabel(
                        row,
                        text=str(username),
                        font=ctk.CTkFont(
                            size=13,
                            weight="bold"
                        )
                    ).pack(
                        side="left"
                    )

                    ctk.CTkLabel(
                        row,
                        text=f"{float(value):.2f} CPS",
                        font=ctk.CTkFont(
                            size=14,
                            weight="bold"
                        )
                    ).pack(
                        side="right",
                        padx=12
                    )

            else:

                ctk.CTkLabel(
                    self.online_cps_frame,
                    text="No online CPS results yet.",
                    text_color=MUTED
                ).pack(
                    anchor="w",
                    padx=10,
                    pady=(0, 8)
                )

            # ---------------------------------------------
            # Reaction
            # ---------------------------------------------

            ctk.CTkLabel(
                self.online_reaction_frame,
                text="? TOP 3 REACTION",
                font=ctk.CTkFont(
                    size=16,
                    weight="bold"
                )
            ).pack(
                anchor="w",
                padx=10,
                pady=(12, 4)
            )

            if reaction:

                for index, item in enumerate(reaction[:3]):

                    username = item.get(
                        "username",
                        "Player"
                    )

                    value = item.get(
                        "value",
                        0
                    )

                    row = ctk.CTkFrame(
                        self.online_reaction_frame,
                        fg_color=HOVER if index == 0 else "transparent",
                        corner_radius=8
                    )

                    row.pack(
                        fill="x",
                        pady=2
                    )

                    ctk.CTkLabel(
                        row,
                        text=medals[index],
                        font=ctk.CTkFont(size=20)
                    ).pack(
                        side="left",
                        padx=(10, 10),
                        pady=7
                    )

                    ctk.CTkLabel(
                        row,
                        text=str(username),
                        font=ctk.CTkFont(
                            size=13,
                            weight="bold"
                        )
                    ).pack(
                        side="left"
                    )

                    ctk.CTkLabel(
                        row,
                        text=f"{float(value):.0f} ms",
                        font=ctk.CTkFont(
                            size=14,
                            weight="bold"
                        )
                    ).pack(
                        side="right",
                        padx=12
                    )

            else:

                ctk.CTkLabel(
                    self.online_reaction_frame,
                    text="No online reaction results yet.",
                    text_color=MUTED
                ).pack(
                    anchor="w",
                    padx=10,
                    pady=(0, 8)
                )

            self.online_status.configure(
                text="Online leaderboard connected ?",
                text_color=GREEN
            )

            now = time.strftime(
                "%H:%M:%S"
            )

            self.online_last_update.configure(
                text=f"Last leaderboard update: {now}"
            )

        except Exception as e:

            print(
                "Online leaderboard display error:",
                e
            )

            try:
                self.online_status.configure(
                    text="Could not display online leaderboard.",
                    text_color=RED
                )
            except Exception:
                pass

    # ========================================================
    # PROFILE
    # ========================================================

    def show_profile(self):

        self.clear()

        self.page_title(
            "Profile",
            "Customize your profile."
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
            data["username"]
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

        data["username"] = username

        save_data()

        self.update_sidebar_rank()

        self.show_profile()


if __name__ == "__main__":

    print("Starting SliqTest...")

    try:

        app = SliqTest()

        print("SliqTest started successfully.")

        app.mainloop()

    except Exception as e:

        print("")
        print("================================")
        print("SLIQTEST ERROR")
        print("================================")
        print(e)
        print("================================")
        input("Press ENTER to close...")

