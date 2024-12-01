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
        data = story.strip("{}")
        items = data.split(", ", 4)

        if len(items) != 5:
            return {"error": "프롬프트 오류, 다시 시도해주세요."}

        story_name = items[3].split(": ")[1].strip("'")
        story_content = items[4].split(": ")[1].strip("'")
        
        print(f"filename: {file.filename}\n story_name: {story_name}\n story_content: {story_content}")

    except client.error.InvalidRequestError as e:
        return {"error": f"객체 검출 중 오류 발생: {str(e)}"}
    

    return {
            "filename": file.filename,
            "story_name": story_name,
            "story_content": story_content,
        }
    
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
