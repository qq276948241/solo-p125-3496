import hashlib
import secrets
import sqlite3
from fastapi import Header, HTTPException, status
from .database import get_db


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    hashed = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{hashed}"


def verify_password(password: str, password_hash: str) -> bool:
    salt, stored_hash = password_hash.split(":")
    computed = hashlib.sha256((salt + password).encode()).hexdigest()
    return computed == stored_hash


def get_member_by_token(authorization: str = Header(None)) -> sqlite3.Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization[7:]
    parts = token.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )
    try:
        member_id = int(parts[0])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    db = get_db()
    member = db.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    db.close()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Member not found",
        )
    return member


def get_coach_by_token(authorization: str = Header(None)) -> sqlite3.Row:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )
    token = authorization[7:]
    parts = token.split(":", 1)
    if len(parts) != 2:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format",
        )
    try:
        coach_id = int(parts[0])
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    db = get_db()
    coach = db.execute("SELECT * FROM coaches WHERE id = ?", (coach_id,)).fetchone()
    db.close()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Coach not found",
        )
    return coach
