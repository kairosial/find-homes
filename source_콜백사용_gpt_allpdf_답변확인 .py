from flask import Flask, request, jsonify
from RAG import generate_answer_with_rag
from QR import query_rewrite
import threading
import time
import json
import requests

app = Flask(__name__)

# 사용자별 source_filter 저장
user_file_choices = {}

@app.route("/kakao-webhook", methods=["POST"])
def kakao_webhook():
    req = request.get_json()
    print(req)
    user_input = req['userRequest']['utterance']
    user_id = req['userRequest']['user']['id']
    callback_url = req['userRequest'].get('callbackUrl')
    source_filter = req.get("action", {}).get("clientExtra", {}).get("source_filter")


    print("📥 질문 수신:", user_input)
    print("🔁 callback_url:", callback_url)
    print("🔑 source_filter:", source_filter)

    # (1) 선택완료 블록에서 들어온 요청: source_filter 저장만
    if source_filter:
        user_file_choices[user_id] = source_filter
        print(f"✅ source_filter 저장됨: {user_id} → {source_filter}")
        # 카카오 오픈빌더에서 응답을 지정해뒀기 때문에 Flask에서는 응답 템플릿 불필요
        return jsonify({ "status": "ok" })  # 최소한의 응답

    # (2) 폴백 블록: 실제 질문 처리
    chosen_file = user_file_choices.get(user_id)

    # 선택이 안 된 경우
    if not chosen_file:
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{
                    "simpleText": {"text": "❗먼저 '도움말'에서 파일을 선택해주세요."}
                }]
            }
        })

    user_input = query_rewrite(user_input)

    if callback_url:
        threading.Thread(target=process_request, args=(user_input, callback_url, chosen_file)).start()
        return jsonify({
            "version": "2.0",
            "useCallback": True,
            "data": { "text": "" }
        })
    else:
        answer = generate_answer_with_rag(user_input, source_filter=chosen_file)
        return jsonify({
            "version": "2.0",
            "template": {
                "outputs": [{ "simpleText": { "text": answer } }]
            }
        })

def process_request(user_input, callback_url, source_filter):
    print("⏱ 백그라운드에서 LLM 처리 시작")
    start = time.time()

    answer = generate_answer_with_rag(user_input, source_filter)
    elapsed = time.time() - start
    print(f"✅ 응답 완료 (처리 시간: {elapsed:.2f}초)")

    response_body = {
        "version": "2.0",
        "template": {
            "outputs": [{ "simpleText": { "text": answer } }]
        }
    }
    headers = { "Content-Type": "application/json" }

    try:
        resp = requests.post(callback_url, headers=headers, json=response_body)
        print("📤 Callback 응답 전송, 상태 코드:", resp.status_code)
    except Exception as e:
        print("❌ Callback 전송 실패:", e)

if __name__ == "__main__":
    print("✅ Flask 서버 실행 중 (port 5000)...")
    app.run(port=5000)
