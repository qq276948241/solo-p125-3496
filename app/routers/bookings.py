from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from ..database import get_db
from ..models import BookingCreate, BookingReschedule, BookingOut, BookingOutDetail
from ..auth import get_member_by_token

router = APIRouter(prefix="/bookings", tags=["预约管理"])


@router.post("/", response_model=BookingOut, status_code=201)
def create_booking(data: BookingCreate, member=Depends(get_member_by_token)):
    if member["id"] != data.member_id:
        raise HTTPException(status_code=403, detail="只能为自己预约")

    db = get_db()

    coach = db.execute("SELECT * FROM coaches WHERE id = ?", (data.coach_id,)).fetchone()
    if not coach:
        raise HTTPException(status_code=404, detail="教练不存在")

    course = db.execute("SELECT * FROM courses WHERE id = ?", (data.course_id,)).fetchone()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    if not course["is_active"]:
        raise HTTPException(status_code=400, detail="课程已停用")

    duration = course["duration_minutes"]
    start_str = data.start_time.strftime("%H:%M")
    start_dt = datetime.strptime(start_str, "%H:%M")
    end_dt = start_dt + timedelta(minutes=duration)
    end_str = end_dt.strftime("%H:%M")
    booking_date_str = data.booking_date.isoformat()

    conflict = db.execute(
        """
        SELECT id FROM bookings
        WHERE member_id = ? AND booking_date = ? AND status = 'booked'
        AND (
            (start_time < ? AND end_time > ?)
            OR (start_time < ? AND end_time > ?)
            OR (start_time >= ? AND end_time <= ?)
        )
        """,
        (
            member["id"], booking_date_str,
            end_str, start_str,
            end_str, end_str,
            start_str, end_str,
        ),
    ).fetchone()
    if conflict:
        raise HTTPException(status_code=409, detail="该时段已有预约，不可重复下单")

    coach_conflict = db.execute(
        """
        SELECT id FROM bookings
        WHERE coach_id = ? AND booking_date = ? AND status = 'booked'
        AND (
            (start_time < ? AND end_time > ?)
            OR (start_time < ? AND end_time > ?)
            OR (start_time >= ? AND end_time <= ?)
        )
        """,
        (
            data.coach_id, booking_date_str,
            end_str, start_str,
            end_str, end_str,
            start_str, end_str,
        ),
    ).fetchone()
    if coach_conflict:
        raise HTTPException(status_code=409, detail="教练该时段已有排课")

    sessions_cost = course["price_sessions"]
    if member["remaining_sessions"] < sessions_cost:
        raise HTTPException(status_code=400, detail=f"课时不足，需要{sessions_cost}节，当前剩余{member['remaining_sessions']}节")

    db.execute(
        "UPDATE members SET remaining_sessions = remaining_sessions - ? WHERE id = ?",
        (sessions_cost, member["id"]),
    )

    cursor = db.execute(
        """
        INSERT INTO bookings (member_id, coach_id, course_id, booking_date, start_time, end_time, status, sessions_cost)
        VALUES (?, ?, ?, ?, ?, ?, 'booked', ?)
        """,
        (member["id"], data.coach_id, data.course_id, booking_date_str, start_str, end_str, sessions_cost),
    )
    db.commit()

    booking = db.execute("SELECT * FROM bookings WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(booking)


@router.get("/", response_model=list[BookingOutDetail])
def list_bookings(member_id: int = None, coach_id: int = None, status_filter: str = None):
    db = get_db()
    query = """
        SELECT b.*, m.name AS member_name, c.name AS coach_name, co.name AS course_name
        FROM bookings b
        JOIN members m ON b.member_id = m.id
        JOIN coaches c ON b.coach_id = c.id
        JOIN courses co ON b.course_id = co.id
        WHERE 1=1
    """
    params = []
    if member_id is not None:
        query += " AND b.member_id = ?"
        params.append(member_id)
    if coach_id is not None:
        query += " AND b.coach_id = ?"
        params.append(coach_id)
    if status_filter:
        query += " AND b.status = ?"
        params.append(status_filter)

    query += " ORDER BY b.booking_date DESC, b.start_time DESC"
    rows = db.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/{booking_id}", response_model=BookingOutDetail)
def get_booking(booking_id: int):
    db = get_db()
    row = db.execute(
        """
        SELECT b.*, m.name AS member_name, c.name AS coach_name, co.name AS course_name
        FROM bookings b
        JOIN members m ON b.member_id = m.id
        JOIN coaches c ON b.coach_id = c.id
        JOIN courses co ON b.course_id = co.id
        WHERE b.id = ?
        """,
        (booking_id,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="预约不存在")
    return dict(row)


@router.put("/{booking_id}/reschedule", response_model=BookingOut)
def reschedule_booking(booking_id: int, data: BookingReschedule, member=Depends(get_member_by_token)):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking["member_id"] != member["id"]:
        raise HTTPException(status_code=403, detail="只能修改自己的预约")
    if booking["status"] != "booked":
        raise HTTPException(status_code=400, detail="只能修改待上课的预约")

    course = db.execute("SELECT * FROM courses WHERE id = ?", (booking["course_id"],)).fetchone()
    duration = course["duration_minutes"]
    start_str = data.start_time.strftime("%H:%M")
    start_dt = datetime.strptime(start_str, "%H:%M")
    end_dt = start_dt + timedelta(minutes=duration)
    end_str = end_dt.strftime("%H:%M")
    booking_date_str = data.booking_date.isoformat()

    conflict = db.execute(
        """
        SELECT id FROM bookings
        WHERE member_id = ? AND booking_date = ? AND status = 'booked' AND id != ?
        AND (
            (start_time < ? AND end_time > ?)
            OR (start_time < ? AND end_time > ?)
            OR (start_time >= ? AND end_time <= ?)
        )
        """,
        (
            member["id"], booking_date_str, booking_id,
            end_str, start_str,
            end_str, end_str,
            start_str, end_str,
        ),
    ).fetchone()
    if conflict:
        raise HTTPException(status_code=409, detail="新时段与已有预约冲突")

    coach_conflict = db.execute(
        """
        SELECT id FROM bookings
        WHERE coach_id = ? AND booking_date = ? AND status = 'booked' AND id != ?
        AND (
            (start_time < ? AND end_time > ?)
            OR (start_time < ? AND end_time > ?)
            OR (start_time >= ? AND end_time <= ?)
        )
        """,
        (
            booking["coach_id"], booking_date_str, booking_id,
            end_str, start_str,
            end_str, end_str,
            start_str, end_str,
        ),
    ).fetchone()
    if coach_conflict:
        raise HTTPException(status_code=409, detail="教练新时段已有排课")

    db.execute(
        """
        UPDATE bookings SET booking_date = ?, start_time = ?, end_time = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (booking_date_str, start_str, end_str, booking_id),
    )
    db.commit()

    updated = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    return dict(updated)


@router.put("/{booking_id}/cancel")
def cancel_booking(booking_id: int, member=Depends(get_member_by_token)):
    db = get_db()
    booking = db.execute("SELECT * FROM bookings WHERE id = ?", (booking_id,)).fetchone()
    if not booking:
        raise HTTPException(status_code=404, detail="预约不存在")
    if booking["member_id"] != member["id"]:
        raise HTTPException(status_code=403, detail="只能取消自己的预约")
    if booking["status"] != "booked":
        raise HTTPException(status_code=400, detail="该预约无法取消")

    booking_datetime = datetime.strptime(
        f"{booking['booking_date']} {booking['start_time']}", "%Y-%m-%d %H:%M"
    )
    now = datetime.now()
    hours_until_class = (booking_datetime - now).total_seconds() / 3600

    sessions_cost = booking["sessions_cost"]
    if hours_until_class < 24:
        refund = sessions_cost // 2
        detail_msg = f"距上课不足24小时，扣除一半课时，退还{refund}节"
    else:
        refund = sessions_cost
        detail_msg = f"距上课超过24小时，全额退还{refund}节课时"

    db.execute(
        "UPDATE members SET remaining_sessions = remaining_sessions + ? WHERE id = ?",
        (refund, member["id"]),
    )
    db.execute(
        "UPDATE bookings SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (booking_id,),
    )
    db.commit()

    return {
        "message": detail_msg,
        "refund_sessions": refund,
        "deducted_sessions": sessions_cost - refund,
    }
