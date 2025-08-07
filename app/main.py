from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import auth, course, semester, timetable
from fastapi.routing import APIRoute

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "https://edudash-eight.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(course.router)
app.include_router(semester.router)
app.include_router(timetable.router)

for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"Path: {route.path} | Methods: {route.methods}")


@app.get("/")
def root():
    return {"message": "Academate API (MongoDB) is running 🚀"}
