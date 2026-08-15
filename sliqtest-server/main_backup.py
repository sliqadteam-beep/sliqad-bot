from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
import hashlib
import secrets
import time

app = FastAPI(title="SliqTest API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB = "sliqtest.db"


def db():
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            test_type TEXT NOT NULL,
            value REAL NOT NULL,
            created_at INTEGER NOT NULL
        )
    """)

    connection.commit()
    connection.close()


init_db()


class Account(BaseModel):
    username: str
    password: str


class Result(BaseModel):
    username: str
    test_type: str
    value: float


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.get("/")
def home():
    return {
        "name": "SliqTest API",
        "status": "online"
    }


@app.get("/leaderboard")
def leaderboard():
    connection = db()

    cps = connection.execute("""
        SELECT username, value
        FROM results
        WHERE test_type = 'cps'
        ORDER BY value DESC
        LIMIT 3
    """).fetchall()

    reaction = connection.execute("""
        SELECT username, value
        FROM results
        WHERE test_type = 'reaction'
        ORDER BY value ASC
        LIMIT 3
    """).fetchall()

    connection.close()

    return {
        "cps": [
            {
                "username": row["username"],
                "value": row["value"]
            }
            for row in cps
        ],
        "reaction": [
            {
                "username": row["username"],
                "value": row["value"]
            }
            for row in reaction
        ],
        "updated": int(time.time())
    }


@app.post("/register")
def register(account: Account):
    username = account.username.strip()

    if len(username) < 2:
        raise HTTPException(400, "Username is too short.")

    if len(account.password) < 4:
        raise HTTPException(400, "Password is too short.")

    connection = db()

    try:
        connection.execute(
            """
            INSERT INTO users
            (username, password_hash, created_at)
            VALUES (?, ?, ?)
            """,
            (
                username,
                hash_password(account.password),
                int(time.time())
            )
        )

        connection.commit()

    except sqlite3.IntegrityError:
        connection.close()
        raise HTTPException(409, "Username already exists.")

    connection.close()

    return {
        "success": True,
        "username": username
    }


@app.post("/login")
def login(account: Account):
    connection = db()

    user = connection.execute(
        """
        SELECT username, password_hash
        FROM users
        WHERE username = ?
        """,
        (account.username.strip(),)
    ).fetchone()

    connection.close()

    if not user:
        raise HTTPException(401, "Invalid username or password.")

    if user["password_hash"] != hash_password(account.password):
        raise HTTPException(401, "Invalid username or password.")

    token = secrets.token_urlsafe(32)

    return {
        "success": True,
        "username": user["username"],
        "token": token
    }


@app.post("/result")
def submit_result(result: Result):

    if result.test_type not in ["cps", "reaction"]:
        raise HTTPException(400, "Invalid test type.")

    if result.test_type == "cps":
        if result.value <= 0 or result.value > 1000:
            raise HTTPException(400, "Invalid CPS result.")

    if result.test_type == "reaction":
        if result.value <= 0 or result.value > 10000:
            raise HTTPException(400, "Invalid reaction result.")

    connection = db()

    connection.execute(
        """
        INSERT INTO results
        (username, test_type, value, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            result.username.strip(),
            result.test_type,
            result.value,
            int(time.time())
        )
    )

    connection.commit()
    connection.close()

    return {
        "success": True
    }
