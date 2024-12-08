from fastapi import Depends, FastAPI, File, UploadFile, HTTPException
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pydantic import BaseModel, EmailStr
from typing import Optional
import os
import sys
import base64
from dotenv import load_dotenv
import uvicorn

from Capstone_DB import init_db, SessionLocal, Story, Image, ImageInfo, User  # Capstone_DB 모듈에서 필요한 클래스 및 함수 가져오기


# --- 초기 설정 ---

#경로 설정
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()
UPLOAD_DIRECTORY = os.getenv("UPLOAD_DIRECTORY", "images/")

#FastAPI 초기화
app = FastAPI()
client = OpenAI()

# OpenAI 설정
client.api_key = os.getenv("OPENAI_API_KEY")

origins = [
    "http://localhost:5173",
    "http://localhost:5173/*",
]

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- 데이터 모델 ---

# Pydantic 모델
class LoginRequest(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    name: str
    password: str
    email: Optional[EmailStr] = None

#아이디 중복체크
class CheckDuplicateRequest(BaseModel):
    username: str

class CheckDuplicateResponse(BaseModel):
    exists: bool


#DB 종속성 체크
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 동화 저장
def save_story(filename: str, story_name: str, story_content: str, image_id: int, user_id: int = 1):
    db = SessionLocal()
    story = Story(
        filename=filename,
        story_name=story_name,
        story_content=story_content,
        image_id=image_id,
        user_id=user_id
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    db.close()
    
# 이미지 정보 저장
def save_image_info(image_id: int, image_url: str, image_description: str = ""):
    db = SessionLocal()
    image_info = ImageInfo(
        image_id=image_id,
        image_url=image_url,
        image_description=image_description
    )
    db.add(image_info)
    db.commit()
    db.refresh(image_info)
    db.close()

# 이미지 저장
def save_image(file: UploadFile, user_id: int = 1) -> int:
    db = SessionLocal()
    image = Image(
        user_id=user_id,  # 기본 사용자 ID -> 추후 회원 가입, 로그인 기능 추가시 변경
        original_filename=file.filename
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    image_id = image.image_id
    db.close()
    return image_id


# --- 함수 정의 ---

# 이미지 인코딩
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# ChatGPT를 사용하여 이미지에서 동화 생성
def detect_story_with_chatgpt(image_path):
    base64_image = encode_image(image_path)
    prompt = (
        "다음은 업로드된 이미지 파일에 대한 분석 작업입니다. 다음 단계에 따라 작업을 수행하세요:"
        "1. 이미지의 내용을 간결하고 명확하게 묘사하세요."
        "2. 이미지에서 주요한 객체 3개를 식별하고, 각 객체를 간략히 설명하세요."
        "3. 식별된 3개의 객체를 중심으로 창의적이고 감동적인 500자 분량의 동화를 작성하세요."
        "4. 최종 출력은 다음 형식의 내용만 제공하세요: {객체1, 객체2, 객체3, 동화 제목: '동화 제목', 동화 내용: '동화 내용'}."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                        "role": "user",
                        "content": [
                            {
                            "type": "text",
                            "text": prompt,
                            },
                            {
                            "type": "image_url",
                            "image_url": {
                                "url":  f"data:image/jpeg;base64,{base64_image}"
                            },
                            },
                        ],
                    }],
            max_tokens=600
        )
        return response.choices[0].message.content.strip()

    except client.error.InvalidRequestError as e:
        print(f"OpenAI API 호출 오류: {e}")
        return []

# --- API 엔드포인트 ---

# 루트 엔드포인트
@app.get("/")
async def root():
    return {"message": "Welcome to the Server!"}

# 아이디 중복 체크
@app.post("/check-duplicate", response_model=CheckDuplicateResponse)
def check_duplicate(request: CheckDuplicateRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    return {"exists": bool(user)}

# 로그인
@app.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or user.password != request.password:
        raise HTTPException(status_code=400, detail="아이디 또는 비밀번호가 잘못되었습니다.")
    
    return {"user_id": user.user_id, "name": user.name}

# 회원가입
@app.post("/signup")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    new_user = User(
        username=user.username,
        name=user.name,
        password=user.password,
        email=user.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"user_id": new_user.user_id}

# 이미지 업로드
@app.post("/image-upload")
async def upload_image(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())

    image_id = save_image(file, user_id=1) 

    image_url = f"http://localhost:8000/images/{file.filename}"
    save_image_info(image_id, image_url)

    try:
        story = detect_story_with_chatgpt(file_location)
        data = story.strip("{}")
        items = data.split(", ", 4)

        if len(items) != 5:
            return {"error": "프롬프트 오류, 다시 시도해주세요."}

        story_name = items[3].split(": ")[1].strip("'")
        story_content = items[4].split(": ")[1].strip("'")
        
        save_story(file.filename, story_name, story_content, image_id, 1)  # 기본 사용자 ID (admin)

        print(f"filename: {file.filename}\nstory_name: {story_name}\nstory_content: {story_content}")

    except client.error.InvalidRequestError as e:
        return {"error": f"객체 검출 중 오류 발생: {str(e)}"}

    return {
        "filename": file.filename,
        "story_name": story_name,
        "story_content": story_content,
        "image_url": image_url
    }

@app.on_event("startup")
def startup_event():
    init_db()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
