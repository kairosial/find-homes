from flask import Flask, request, jsonify
#from onlyRAG import generate_answer_with_rag  # 기존 RAG 응답 생성 함수 (LLM 연동 포함)
from RAG import generate_answer_with_rag  # 기존 RAG 응답 생성 함수 (LLM 연동 포함)
import threading
import time
import json
import uuid

app = Flask(__name__)

# 전역 딕셔너리로 최종 답변을 저장 (예: {tracking_id: final_answer})
final_answers = {}

@app.route("/kakao-webhook", methods=["POST"])
def kakao_webhook():
    req = request.get_json()
    user_input = req['userRequest']['utterance']
    print("📥 질문 수신:", user_input)
    
    # 만약 사용자의 발화가 "답변 확인: <tracking_id>" 형식이면,
    # 이미 생성된 최종 답변을 반환합니다.
    if user_input.startswith("답변 확인:"):
        tracking_id = user_input.split(":", 1)[1].strip()
        print("📡 tracking_id received for final answer:", tracking_id)
        final_answer = final_answers.get(tracking_id)
        if final_answer:
            response_body = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": final_answer
                            }
                        }
                    ]
                }
            }
        else:
            # 최종 답변이 아직 준비되지 않은 경우
            response_body = {
                "version": "2.0",
                "template": {
                    "outputs": [
                        {
                            "simpleText": {
                                "text": "아직 답변이 생성되지 않았습니다. 잠시 후 다시 시도해 주세요."
                            }
                        }
                    ]
                }
            }
        return jsonify(response_body)

    # 그렇지 않은 경우, 새로운 질문이 들어온 것으로 보고 처리 시작
    # 새로운 질문에 대해 고유의 tracking_id를 생성합니다.
    tracking_id = str(uuid.uuid4())
    # 백그라운드 스레드로 LLM 처리를 시작하여 최종 답변을 생성하고 storage에 저장합니다.
    threading.Thread(target=process_request, args=(user_input, tracking_id)).start()

    # 초기 응답을 바로 반환합니다.
    # 이 응답에는 "답변 확인" 버튼(quick reply)이 포함되어 있어,
    # 사용자가 버튼을 누르면 "답변 확인: <tracking_id>"라는 메시지가 전송됩니다.
    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "답변 생성 중입니다. 아래 버튼을 눌러 최종 답변을 확인하세요."
                    }
                }
            ],
            "quickReplies": [
                {
                    "action": "block",
                    "label": "답변 확인",
                    "messageText": f"답변 확인: {tracking_id}"
                }
            ]
        }
    }
    print("💡 초기 응답 반환:", json.dumps(response_body, ensure_ascii=False, indent=2))
    return jsonify(response_body)

def process_request(user_input, tracking_id):
    print("⏱ 백그라운드에서 LLM 처리 시작. tracking_id:", tracking_id)
    answer = generate_answer_with_rag(user_input)
    if not answer or not isinstance(answer, str):
        answer = "⚠️ 답변을 생성하지 못했습니다."
    # 최종 답변을 전역 딕셔너리에 저장 (추후 답변 확인 시 참조)
    final_answers[tracking_id] = answer
    print(f"✅ 최종 답변이 생성되었습니다. (tracking_id: {tracking_id})")
    print("💬 최종 답변:", answer)

if __name__ == "__main__":
    print("✅ Flask 서버 실행 중 (port 5000)...")
    app.run(port=5000)
