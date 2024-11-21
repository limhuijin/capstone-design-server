from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware  # CORS 미들웨어 임포트
import openai
import os
from dotenv import load_dotenv
import aiofiles
from PIL import Image

app = FastAPI()

# CORS 미들웨어 설정
origins = [
    "http://localhost:5173",
    "http://localhost:5173/*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 허용할 출처(origin) 목록
    allow_credentials=True,
    allow_methods=["*"],  # 모든 HTTP 메서드를 허용
    allow_headers=["*"],  # 모든 헤더를 허용
)

# OpenAI API 키 설정
openai.api_key = os.getenv("OPENAI_API_KEY")
UPLOAD_DIRECTORY = "C:/project/capstone-design-server/images"

@app.post("/image-upload")
async def upload_image(file: UploadFile = File(...)):
    if not os.path.exists(UPLOAD_DIRECTORY):
        os.makedirs(UPLOAD_DIRECTORY)

    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    
    # 이미지 파일을 서버에 저장
    async with aiofiles.open(file_location, 'wb') as out_file:
        content = await file.read()
        await out_file.write(content)

    # 이미지 설명을 요청
    response1 = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # 올바른 모델 이름
        messages=[{
            "role": "user",
            "content": f"Describe the content of the image located at {file_location}"
        }],
        max_tokens=100,
    )
    image_description = response1.choices[0].message["content"].strip()

    # 객체 추출을 위한 예시 요청
    response2 = openai.ChatCompletion.create(
        model="gpt-4o-mini",  # 올바른 모델 이름
        messages=[{
            "role": "user",
            "content": "Extract objects from the following image description: " + image_description
        }]
    )
    haiku_response = response2.choices[0].message["content"].strip()

    objects = haiku_response.split(",")  # 실제 응답을 기반으로 수정해야 합니다.

    return {"filename": file.filename, "objects": objects}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
