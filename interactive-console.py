import os
import sys
import requests
import re
from typing import Dict, List, Any
from dotenv import load_dotenv

load_dotenv()

# 🔧 환경변수 설정
AZURE_SEARCH_API_KEY = os.getenv("AI_Search_API_KEY")
AZURE_SEARCH_ENDPOINT = os.getenv("AI_Search_ENDPOINT")
AZURE_SEARCH_INDEX = "new_pdf_all_index"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_ENDPOINT = os.getenv("Embedding_ENDPOINT")
OPENAI_LLM_ENDPOINT = os.getenv("OPENAI_ENDPOINT")

# ✅ 사용자 세션 변수
user_profile = None
user_documents = []

# 🔹 OpenAI 임베딩 요청
def get_embedding(text: str) -> List[float]:
    headers = {
        "Content-Type": "application/json",
        "api-key": OPENAI_API_KEY
    }

    body = {
        "input": text,
        "model": "text-embedding-3-small"
    }

    response = requests.post(OPENAI_EMBEDDING_ENDPOINT, headers=headers, json=body)
    response.raise_for_status()
    embedding = response.json()["data"][0]["embedding"]
    return embedding

# 🔍 Azure AI Search 요청
def request_ai_search(query: str, source_filter: str = None, k: int = 5) -> List[Dict[str, Any]]:
    vector = get_embedding(query)

    url = f"{AZURE_SEARCH_ENDPOINT}/indexes/{AZURE_SEARCH_INDEX}/docs/search?api-version=2023-11-01"
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_SEARCH_API_KEY
    }

    body = {
        "vectorQueries": [{
            "kind": "vector",
            "vector": vector,
            "k": k,
            "fields": "embedding"
        }],
        "select": "content,source"
    }

    if source_filter:
        body["filter"] = f"source eq '{source_filter}'"

    response = requests.post(url, headers=headers, json=body)
    response.raise_for_status()

    results = response.json().get("value", [])
    return [{
        "content": doc["content"],
        "source": doc["source"],
        "score": doc.get("@search.score", 0)
    } for doc in results]

# 🧠 GPT-4o로 응답 생성
def request_gpt(prompt: str) -> str:
    headers = {
        "Content-Type": "application/json",
        "api-key": OPENAI_API_KEY
    }

    body = {
        "messages": [
            {
                "role": "system",
                "content": "너는 친절하고 정확한 AI 도우미야. 사용자 질문에 문서 기반으로 답해줘."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "top_p": 0.95,
        "max_tokens": 800
    }

    response = requests.post(OPENAI_LLM_ENDPOINT, headers=headers, json=body)
    response.raise_for_status()

    message = response.json()["choices"][0]["message"]
    content = re.sub(r'\[doc(\d+)\]', r'[참조 \1]', message['content'])
    return content

# 📄 GPT와 RAG 연결
def generate_answer_with_rag(query: str, source_filter: str = None, top_k: int = 3) -> str:
    results = request_ai_search(query, source_filter=source_filter, k=top_k)

    if not results:
        return "❌ 관련 문서를 찾을 수 없습니다."

    context = "\n\n".join([f"[doc{i+1}]\n{item['content']}" for i, item in enumerate(results)])

    prompt = f"""다음은 사용자가 질문한 내용과 관련된 문서 내용이야. 이 문서를 참고해서 질문에 대해 정확하고 구체적으로 답변해줘.
그리고 어떤 문서에서 찾았는지도 출처도 알려줘.

[사용자 질문]
{query}

[참고 문서]
{context}

답변:"""

    return request_gpt(prompt)

# 👤 사용자 등록
def register_user(age: int, marital_status: bool, region: str) -> str:
    global user_profile, user_documents

    user_profile = {
        "age": age,
        "marital_status": marital_status,
        "region": region
    }

    marital_str = "기혼" if marital_status else "미혼"
    personalized_query = f"{age}대 {marital_str} {region} 거주자 대상 지원금"

    try:
        search_results = request_ai_search(personalized_query, k=3)
    except Exception as e:
        return f"❌ 검색 오류: {str(e)}"

    if not search_results:
        return "❌ 관련 공고문을 찾을 수 없습니다."

    user_documents = search_results
    sources = ", ".join(doc["source"] for doc in search_results)

    return f"✅ 정보가 등록되었으며, 관련 공고문 {len(search_results)}개가 저장되었습니다.\n저장된 문서: {sources}"

# ❓ 질문 응답
def answer_user_query(query: str) -> str:
    if user_profile is None or not user_documents:
        return "❌ 사용자 정보가 등록되어 있지 않거나, 관련 문서가 없습니다."

    age = user_profile["age"]
    marital_status = "기혼" if user_profile["marital_status"] else "미혼"
    region = user_profile["region"]

    return f"📌 {age}대 {marital_status} {region} 거주자를 위한 답변입니다:\n\n{generate_answer_with_rag(query)}"

# 🔄 세션 초기화
def reset_session():
    global user_profile, user_documents
    user_profile = None
    user_documents = []
    return "✅ 세션이 초기화되었습니다. 새로운 정보를 등록하세요."

# 💬 사용자 입력 처리
def process_user_input(user_input: str) -> str:
    global user_profile

    cmd = user_input.strip().lower()
    if cmd in ["종료", "exit", "quit", "나가기"]:
        return "👋 대화를 종료합니다."
    if cmd in ["초기화", "처음으로", "다시", "reset"]:
        return reset_session()

    if user_profile is None and not ("나이:" in user_input and "결혼:" in user_input and "지역:" in user_input):
        return "👋 안녕하세요! 정보를 입력해주세요.\n형식: '나이: 20대, 결혼: 미혼, 지역: 서울'"

    if "나이:" in user_input and "결혼:" in user_input and "지역:" in user_input:
        try:
            age_str = user_input.split("나이:")[1].split(",")[0].strip()
            age = int(age_str.replace("대", ""))

            marital_str = user_input.split("결혼:")[1].split(",")[0].strip()
            marital_status = True if "기혼" in marital_str else False

            region = user_input.split("지역:")[1].split(",")[0].strip()
            return register_user(age, marital_status, region)
        except Exception as e:
            return f"❌ 입력 오류: {str(e)}"

    return answer_user_query(user_input)

# 🚀 콘솔 실행
if __name__ == "__main__":
    print("💬 개인화 공고문 검색 시스템 시작")
    print("📝 형식: '나이: 20대, 결혼: 미혼, 지역: 서울'")
    print("🔁 초기화: '초기화'")
    print("❌ 종료: '종료'")
    print("-" * 50)

    while True:
        user_input = input("\n👤 사용자: ")
        if user_input.strip().lower() in ["종료", "exit", "quit", "나가기"]:
            print("👋 대화를 종료합니다.")
            break

        response = process_user_input(user_input)
        print(f"\n🤖 봇: {response}")
