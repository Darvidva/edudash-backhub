from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import auth, course, models, semester
from .database import engine

app = FastAPI()

@app.on_event("startup")
def on_startup():
    models.Base.metadata.create_all(bind=engine)

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

@app.get("/")
def root():
    return {"message": "Academate API is running 🚀"}
