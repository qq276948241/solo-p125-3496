from fastapi import FastAPI
from .database import init_db
from .routers import members, coaches, courses, bookings

app = FastAPI(
    title="健身房私教课预约系统",
    description="会员注册登录、教练排课、课程管理、预约下单改期取消",
    version="1.0.0",
)

app.include_router(members.router)
app.include_router(coaches.router)
app.include_router(courses.router)
app.include_router(bookings.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root():
    return {"message": "健身房私教课预约系统 API", "docs": "/docs"}
