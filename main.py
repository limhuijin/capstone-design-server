from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import os
from dotenv import load_dotenv
import uvicorn
import base64

load_dotenv()

app = FastAPI()
openai = OpenAI()

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
openai.api_key = os.getenv("OPENAI_API_KEY")
UPLOAD_DIRECTORY = "./images"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

# ChatGPT를 사용한 객체 검출 함수
def detect_objects_with_chatgpt(image_path):
    base64_image = encode_image(image_path)
    prompt1 = (
        "다음은 업로드된 이미지 파일에 대한 분석 작업입니다:\n"
        "이 이미지를 묘사하고, 그 안에서 주요한 3가지 객체를 텍스트로 반환해 주세요. "
        "결과는 쉼표로 구분된 형식으로 작성해 주세요."
    )

    try:
        response1 = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                        "role": "user",
                        "content": [
                            {
                            "type": "text",
                            "text": prompt1,
                            },
                            {
                            "type": "image_url",
                            "image_url": {
                                "url":  f"data:image/jpeg;base64,{base64_image}"
                            },
                            },
                        ],
                    }],
            max_tokens=100,
            temperature=0.7
        )
        result = response1.choices[0].message.content.strip()
        return [obj.strip() for obj in result.split(",") if obj.strip()]
    except openai.error.InvalidRequestError as e:
        print(f"OpenAI API 호출 오류: {e}")
        return []

# ChatGPT를 사용한 동화 생성 함수
def generate_story(objects):
    if not objects:
        return "객체가 감지되지 않아 동화를 생성할 수 없습니다."

    prompt2 = (
        f"다음 세 가지 객체를 활용하여 500자 분량의 창의적이고 감동적인 동화를 만들어줘: {', '.join(objects)}. "
        "객체들이 서로 연결된 이야기가 되도록 해줘."
    )

    try:
        response2 = openai.chat.completions.create(
            model = "gpt-4o-mini",
            messages = [{
                    "role": "user",
                    "content": [
                        {
                        "type": "text",
                        "text": prompt2
                        }
                    ],
                }],
            max_tokens=600
        )

        return response2.choices[0].message.content.strip()
    
    except openai.error.InvalidRequestError as e:
        print(f"OpenAI API 호출 오류: {e}")
        return f"동화 생성 중 오류 발생: {e}"

# 이미지 업로드 및 처리 엔드포인트
@app.post("/image-upload")
async def upload_image(file: UploadFile = File(...)):
    file_location = os.path.join(UPLOAD_DIRECTORY, file.filename)
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())

    # 객체 검출 수행
    try:
        objects = detect_objects_with_chatgpt(file_location)
        print(f"검출된 객체: {objects}")
    except openai.error.InvalidRequestError as e:
        return {"error": f"객체 검출 중 오류 발생: {str(e)}"}

    # 동화 생성 수행
    try:
        story = generate_story(objects)
        print("동화 생성 완료.")
    except openai.error.InvalidRequestError as e:
        return {"error": f"동화 생성 중 오류 발생: {str(e)}"}

    return {"filename": file.filename, "objects": objects, "story": story}

# 서버 실행
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
