from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import MemberRegister, MemberLogin, MemberOut, SessionTopUp, BookingOutDetail
from ..auth import hash_password, verify_password, get_member_by_token

router = APIRouter(prefix="/members", tags=["会员管理"])


@router.post("/register", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def register(data: MemberRegister):
    db = get_db()
    existing = db.execute("SELECT id FROM members WHERE username = ?", (data.username,)).fetchone()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")

    pw_hash = hash_password(data.password)
    cursor = db.execute(
        "INSERT INTO members (username, password_hash, name, phone) VALUES (?, ?, ?, ?)",
        (data.username, pw_hash, data.name, data.phone),
    )
    db.commit()

    member = db.execute("SELECT * FROM members WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(member)


@router.post("/login")
def login(data: MemberLogin):
    db = get_db()
    member = db.execute("SELECT * FROM members WHERE username = ?", (data.username,)).fetchone()
    if not member or not verify_password(data.password, member["password_hash"]):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token = f"{member['id']}:{member['password_hash'][:16]}"
    return {
        "token": token,
        "member": dict(member),
    }


@router.get("/me", response_model=MemberOut)
def get_profile(member=Depends(get_member_by_token)):
    return dict(member)


@router.post("/topup", response_model=MemberOut)
def topup_sessions(data: SessionTopUp, member=Depends(get_member_by_token)):
    db = get_db()
    db.execute(
        "UPDATE members SET remaining_sessions = remaining_sessions + ? WHERE id = ?",
        (data.sessions, member["id"]),
    )
    db.commit()
    updated = db.execute("SELECT * FROM members WHERE id = ?", (member["id"],)).fetchone()
    return dict(updated)


@router.get("/me/history", response_model=list[BookingOutDetail])
def get_my_history(member=Depends(get_member_by_token)):
    db = get_db()
    rows = db.execute(
        """
        SELECT b.*, m.name AS member_name, c.name AS coach_name, co.name AS course_name
        FROM bookings b
        JOIN members m ON b.member_id = m.id
        JOIN coaches c ON b.coach_id = c.id
        JOIN courses co ON b.course_id = co.id
        WHERE b.member_id = ?
        ORDER BY b.booking_date DESC, b.start_time DESC
        """,
        (member["id"],),
    ).fetchall()
    return [dict(r) for r in rows]
