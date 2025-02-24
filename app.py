from flask import Flask, render_template, jsonify
import requests  # ✅ 여기에서 import 해야 함
import time
import json

app = Flask(__name__)


# 노션 API 설정
NOTION_API_KEY = "secret_IVUUMjyv15f1rUKFj0PAKrEzWr6LzHJqKRrnmH1gfrF"  # 여기에 본인의 노션 API 키 입력
DATABASE_ID = "1a16f73a586080368e0dd54311df4886"  # 여기에 본인의 데이터베이스 ID 입력
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# 📌 메인 데이터베이스 가져오기
def fetch_main_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=HEADERS)

    if response.status_code != 200:
        return {"error": "Failed to fetch main database"}

    data = response.json()
    main_data = []

    for page in data.get("results", []):
        properties = page.get("properties", {})

        # 📌 메인 데이터베이스에서 유지할 속성들
        brand_name = properties.get("브랜드", {}).get("title", [{}])[0].get("plain_text", "No Title")
        reference = properties.get("레퍼런스", {}).get("multi_select", [])
        brand_info = properties.get("브랜드정보", {}).get("rich_text", [{}])[0].get("plain_text", "N/A")

        main_data.append({
            "id": page.get("id"),
            "브랜드": brand_name,
            "레퍼런스": ", ".join([ref["name"] for ref in reference]) if reference else "N/A",
            "브랜드정보": brand_info,
            "created_time": page.get("created_time"),
            "last_edited_time": page.get("last_edited_time"),
            "url": page.get("url")
        })

    return main_data
# 📌 페이지 콘텐츠 가져오기 (데이터베이스 포함)
def fetch_page_content(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    response = requests.get(url, headers=HEADERS)

    if response.status_code != 200:
        return {"error": "Failed to fetch page content"}

    data = response.json()
    page_content = []

    for block in data.get("results", []):
        block_type = block.get("type")
        content_text = ""

        if block_type == "paragraph":
            text_data = block.get("paragraph", {}).get("rich_text", [])
            content_text = "".join([t["plain_text"] for t in text_data])

        elif block_type in ["heading_1", "heading_2", "heading_3"]:
            text_data = block.get(block_type, {}).get("rich_text", [])
            heading_size = block_type[-1]
            content_text = f"<h{heading_size}>" + "".join([t["plain_text"] for t in text_data]) + f"</h{heading_size}>"

        elif block_type == "bulleted_list_item":
            text_data = block.get("bulleted_list_item", {}).get("rich_text", [])
            content_text = "<li>" + "".join([t["plain_text"] for t in text_data]) + "</li>"

        elif block_type == "child_database":  # 서브 데이터베이스가 포함된 경우
            database_id = block.get("id")
            database_title = block.get("child_database", {}).get("title", "No Title")
            database_content = fetch_sub_database(database_id)

            content_text = f"<h3>{database_title}</h3>{database_content}"

        if content_text:
            page_content.append(content_text)

    return {"content": page_content}

# 📌 서브 데이터베이스 가져오기 (고정된 속성값)
def fetch_sub_database(database_id):
    
    # "완료" 그룹에 해당하는 상태명들을 명시합니다.
    complete_statuses = ["CJ 최종 점검", "PO전달 to IBR", "CJ - 본 물량 입고", "CJ - 본 물량 수입", "판매시작"]
    
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    
    response = requests.post(url, headers=HEADERS)

    if response.status_code != 200:
        return "<p>Failed to load sub-database content</p>"

    data = response.json()
    sub_database_content = "<table border='1'><tr>"

    # 컬럼명 고정
    column_names = ["담당자", "업무진행현황", "날짜", "로그"]
    for col in column_names:
        sub_database_content += f"<th>{col}</th>"
    sub_database_content += "</tr>"

    for page in data.get("results", []):
        properties = page.get("properties", {})

        status_property = properties.get("업무진행현황", {}).get("status", {})
        status_name = status_property.get("name", "N/A")

        if status_name not in complete_statuses:
            continue
        
        sub_database_content += "<tr>"
        
        담당자 = ", ".join([p["name"] for p in properties.get("담당자", {}).get("people", [])]) if properties.get("담당자") else "N/A"
        날짜 = properties.get("날짜", {}).get("date", {}).get("start", "N/A")
        rich_text_list = properties.get("로그", {}).get("rich_text", [])
        로그 = rich_text_list[0]["plain_text"] if rich_text_list else "N/A"

        sub_database_content += f"<td>{담당자}</td><td>{status_name}</td><td>{날짜}</td><td>{로그}</td>"
        sub_database_content += "</tr>"

    sub_database_content += "</table>"
    return sub_database_content

# 📌 기본 페이지 (index) - 메인 데이터베이스 보여줌
@app.route("/")
def home():
    database_id = "1a16f73a586080368e0dd54311df4886"  # 👉 메인 데이터베이스 ID 입력
    data = fetch_main_database(database_id)
    return render_template("index.html", data=data)

# 📌 특정 페이지 콘텐츠 가져오기
@app.route("/get-page-content/<page_id>")
def get_page_content(page_id):
    print(f"Received request for page_id: {page_id}")
    content = fetch_page_content(page_id)
    return jsonify(content)

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Not Found"}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)