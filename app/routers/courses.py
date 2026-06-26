from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..models import CourseCreate, CourseUpdate, CourseOut

router = APIRouter(prefix="/courses", tags=["课程管理"])


@router.post("/", response_model=CourseOut, status_code=201)
def create_course(data: CourseCreate):
    db = get_db()
    cursor = db.execute(
        "INSERT INTO courses (name, description, price_sessions, duration_minutes) VALUES (?, ?, ?, ?)",
        (data.name, data.description, data.price_sessions, data.duration_minutes),
    )
    db.commit()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(course)


@router.get("/", response_model=list[CourseOut])
def list_courses(active_only: bool = False):
    db = get_db()
    if active_only:
        rows = db.execute("SELECT * FROM courses WHERE is_active = 1 ORDER BY id").fetchall()
    else:
        rows = db.execute("SELECT * FROM courses ORDER BY id").fetchall()
    return [dict(r) for r in rows]


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: int):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return dict(course)


@router.put("/{course_id}", response_model=CourseOut)
def update_course(course_id: int, data: CourseUpdate):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    updates = {}
    if data.name is not None:
        updates["name"] = data.name
    if data.description is not None:
        updates["description"] = data.description
    if data.price_sessions is not None:
        updates["price_sessions"] = data.price_sessions
    if data.duration_minutes is not None:
        updates["duration_minutes"] = data.duration_minutes
    if data.is_active is not None:
        updates["is_active"] = 1 if data.is_active else 0

    if updates:
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [course_id]
        db.execute(f"UPDATE courses SET {set_clause} WHERE id = ?", values)
        db.commit()

    updated = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    return dict(updated)


@router.delete("/{course_id}")
def deactivate_course(course_id: int):
    db = get_db()
    course = db.execute("SELECT * FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")

    db.execute("UPDATE courses SET is_active = 0 WHERE id = ?", (course_id,))
    db.commit()
    return {"message": "课程已停用"}
