from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from ..database import get_db
from ..models import CoachRegister, CoachLogin, CoachOut, BookingOutDetail
from ..auth import hash_password, verify_password, get_coach_by_token

router = APIRouter(prefix="/coaches", tags=["教练管理"])


@router.post("/register", response_model=CoachOut, status_code=201)
def register(data: CoachRegister):
    db = get_db()
    existing = db.execute("SELECT id FROM coaches WHERE username = ?", (data.username,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    pw_hash = hash_password(data.password)
    cursor = db.execute(
        "INSERT INTO coaches (username, password_hash, name, phone, specialty) VALUES (?, ?, ?, ?, ?)",
        (data.username, pw_hash, data.name, data.phone, data.specialty),
    )
    db.commit()

    coach = db.execute("SELECT * FROM coaches WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(coach)


@router.post("/login")
def login(data: CoachLogin):
    db = get_db()
    coach = db.execute("SELECT * FROM coaches WHERE username = ?", (data.username,)).fetchone()
    if not coach or not verify_password(data.password, coach["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = f"{coach['id']}:{coach['password_hash'][:16]}"
    return {
        "token": token,
        "coach": dict(coach),
    }


@router.get("/me", response_model=CoachOut)
def get_profile(coach=Depends(get_coach_by_token)):
    return dict(coach)


@router.get("/me/today", response_model=list[BookingOutDetail])
def get_today_schedule(coach=Depends(get_coach_by_token)):
    db = get_db()
    today = date.today().isoformat()
    rows = db.execute(
        """
        SELECT b.*, m.name AS member_name, c.name AS coach_name, co.name AS course_name
        FROM bookings b
        JOIN members m ON b.member_id = m.id
        JOIN coaches c ON b.coach_id = c.id
        JOIN courses co ON b.course_id = co.id
        WHERE b.coach_id = ? AND b.booking_date = ? AND b.status = 'booked'
        ORDER BY b.start_time
        """,
        (coach["id"], today),
    ).fetchall()
    return [dict(r) for r in rows]


@router.get("/me/week", response_model=list[BookingOutDetail])
def get_week_schedule(coach=Depends(get_coach_by_token)):
    db = get_db()
    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)
    rows = db.execute(
        """
        SELECT b.*, m.name AS member_name, c.name AS coach_name, co.name AS course_name
        FROM bookings b
        JOIN members m ON b.member_id = m.id
        JOIN coaches c ON b.coach_id = c.id
        JOIN courses co ON b.course_id = co.id
        WHERE b.coach_id = ? AND b.booking_date >= ? AND b.booking_date <= ? AND b.status = 'booked'
        ORDER BY b.booking_date, b.start_time
        """,
        (coach["id"], start_of_week.isoformat(), end_of_week.isoformat()),
    ).fetchall()
    return [dict(r) for r in rows]
