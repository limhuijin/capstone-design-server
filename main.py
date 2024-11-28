from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import uvicorn
import base64

load_dotenv()

app = FastAPI()
client = OpenAI()

origins = [
    "http://localhost:5173",
    "http://localhost:5173/*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# OpenAI 설정
client.api_key = os.getenv("OPENAI_API_KEY")
UPLOAD_DIRECTORY = "./images"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def detect_story_with_chatgpt(image_path):
    base64_image = encode_image(image_path)
    prompt = (
        "다음은 업로드된 이미지 파일에 대한 분석 작업입니다:\n"
        "이 이미지를 묘사하고, 그 안에서 주요한 3가지 객체를 찾아내고,"
        "객체를 활용하여 500자 분량의 창의적이고 감동적인 동화를 만들고 동화 내용만 반환해줘"
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

@app.get("/")
async def root():
    return {"message": "Welcome to the Server!"}

@app.post("/image-upload")
async def upload_image(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())

    try:
        story = detect_story_with_chatgpt(file_location)
    except client.error.InvalidRequestError as e:
        return {"error": f"객체 검출 중 오류 발생: {str(e)}"}

    return {"filename": file.filename, "story": story}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
