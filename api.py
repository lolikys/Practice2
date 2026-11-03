from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine, Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from werkzeug.security import check_password_hash, generate_password_hash
import jwt
import datetime
import os


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{BASE_DIR}/instance/Academi.db"
os.makedirs(f"{BASE_DIR}/instance", exist_ok=True)

SECRET_KEY = "super_secret_key_for_jwt"
ALGORITHM = "HS256"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

student_course = Table('student_course', Base.metadata,
    Column('student_id', Integer, ForeignKey('user.id'), primary_key=True),
    Column('course_id', Integer, ForeignKey('course.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "user"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)
    name = Column(String)
    courses = relationship("Course", secondary=student_course, backref="students")

class Course(Base):
    __tablename__ = "course"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    duration = Column(String)
    description = Column(String)

Base.metadata.create_all(bind=engine)
db_init = SessionLocal()
if not db_init.query(User).filter(User.username == 'admin').first():
    admin = User(username='admin', password_hash=generate_password_hash('admin123'), role='admin', name='Администратор')
    db_init.add(admin)
    db_init.commit()
    print("Создан пользователь admin с паролем admin123")
db_init.close()

app = FastAPI(title="Academi Full API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

security = HTTPBearer()

class LoginData(BaseModel):
    username: str
    password: str

class CourseCreate(BaseModel):
    title: str
    duration: str
    description: str = ""

class CourseResponse(BaseModel):
    id: int
    title: str
    duration: str
    description: str | None = None
    model_config = ConfigDict(from_attributes=True)

def get_current_username(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Неверный токен")
        return username
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")

@app.post("/api/login")
def login(data: LoginData):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == data.username).first()
        if not user or not user.password_hash or not check_password_hash(user.password_hash, data.password):
            raise HTTPException(status_code=401, detail="Неверный логин или пароль")
        
        token = jwt.encode({
            "sub": user.username,
            "role": user.role,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, SECRET_KEY, algorithm=ALGORITHM)
        
        return {"access_token": token, "token_type": "bearer", "name": user.name, "role": user.role}
    finally:
        db.close()

@app.get("/api/my-courses", response_model=list[CourseResponse])
def get_my_courses(username: str = Depends(get_current_username)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
            
        if user.role == "admin":
            return db.query(Course).all()
            
        return user.courses
    finally:
        db.close()

@app.post("/api/courses", response_model=CourseResponse)
def create_course(course: CourseCreate, username: str = Depends(get_current_username)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or user.role != "admin":
            raise HTTPException(status_code=403, detail="Только администратор может создавать курсы")
        
        new_course = Course(title=course.title, duration=course.duration, description=course.description)
        db.add(new_course)
        db.commit()
        db.refresh(new_course)
        return new_course
    finally:
        db.close()