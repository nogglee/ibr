from flask import Flask, render_template, jsonify, request
import requests  # ✅ 여기에서 import 해야 함
import time
import json
import math

app = Flask(__name__)


# 노션 API 설정
NOTION_API_KEY = "secret_IVUUMjyv15f1rUKFj0PAKrEzWr6LzHJqKRrnmH1gfrF"  # 여기에 본인의 노션 API 키 입력
DATABASE_ID = "1a16f73a586080368e0dd54311df4886"  # 여기에 본인의 데이터베이스 ID 입력
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# 📌 페이지 콘텐츠 가져오기 (데이터베이스 포함)
def fetch_all_main_database(database_id):
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {"page_size": 100}
    results = []
    while True:
        response = requests.post(url, headers=HEADERS, json=payload)
        if response.status_code != 200:
            break
        data = response.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    return results

def build_main_database_table(results, current_page=1, per_page=50):
    start = (current_page - 1) * per_page
    end = start + per_page
    sliced = results[start:end]
    
    # 컬럼 정의: (표시할 컬럼명, 프로퍼티 타입)
    columns = [
        ("레퍼런스", "multi_select"),
        ("브랜드", "title"),
        ("브랜드정보", "rich_text"),
        ("채택현황", "select"),
        ("카테고리", "multi_select"),
        ("메인아이템", "multi_select"),
        ("브랜드홈페이지", "url"),
        ("우선순위", "select"),
        ("CJ 담당자", "text"),
        ("IBR담당자", "people"),
        ("업무진행현황", "select"),
        ("글로벌담당자", "people"),
        ("수입방법", "select"),
        ("제안사", "select"),
        ("제안일자", "date"),
        ("주요입점", "rich_text"),
        ("국가", "select"),
        ("생성일시", "create_date")
    ]
    
    html = "<table border='1'><tr>"
    # 헤더 생성
    for col_name, _ in columns:
        html += f"<th>{col_name}</th>"
    html += "</tr>"
    
    # 각 행 생성
    for page in sliced:
        properties = page.get("properties", {})
        row = "<tr>"
        for col_name, col_type in columns:
            value = ""
            if col_type == "multi_select":
                items = properties.get(col_name, {}).get("multi_select", [])
                value = ", ".join(item.get("name", "") for item in items) if items else ""
            elif col_type == "title":
                items = properties.get(col_name, {}).get("title", [])
                value = items[0].get("plain_text", "") if items else ""
                if col_name == "브랜드":
                    # 브랜드 셀을 클릭하면 loadPageContent() 호출하여 사이드바에 콘텐츠 표시
                    page_id = page.get("id", "")
                    value = f'<a href="#" onclick="loadPageContent(\'{page_id}\')">{value}</a>'
            elif col_type == "rich_text":
                items = properties.get(col_name, {}).get("rich_text", [])
                value = items[0].get("plain_text", "") if items else ""
            elif col_type == "select":
                sel = properties.get(col_name, {}).get("select", {})
                value = sel.get("name", "") if sel else ""
            elif col_type == "text":
                value = properties.get(col_name, {}).get("text", "") or ""
            elif col_type == "people":
                ppl = properties.get(col_name, {}).get("people", [])
                value = ", ".join(p.get("name", "") for p in ppl) if ppl else ""
            elif col_type == "url":
                value = properties.get(col_name, {}).get("url", "") or ""
            elif col_type == "date":
                date_obj = properties.get(col_name, {}).get("date", {})
                value = date_obj.get("start", "") if date_obj else ""
            elif col_type == "create_date":
                value = page.get("created_time", "")
            row += f"<td>{value}</td>"
        row += "</tr>"
        html += row
    
    html += "</table>"
    return html

# 서브 데이터베이스 가져오기 (고정된 속성값: 담당자, 업무진행현황, 날짜, 로그)
def fetch_sub_database(database_id, brand_id=None):
    complete_statuses = ["CJ 최종 점검", "PO전달 to IBR", "CJ - 본 물량 입고", "CJ - 본 물량 수입", "판매시작"]
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    response = requests.post(url, headers=HEADERS)
    if response.status_code != 200:
        return "<p>Failed to load sub-database content</p>"
    data = response.json()
    sub_database_content = "<table border='1'><tr>"
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

# 페이지 콘텐츠 가져오기 (여기서는 함수 정의만 포함 – 실제 구현 필요)
def fetch_page_content(page_id):
    # 실제 Notion API 호출 로직을 구현해야 하지만, 예시로 간단한 문자열 반환
    return {"content": {page_id}}

@app.route("/")
def index():
    page_num = int(request.args.get("page", 1))
    results = fetch_all_main_database(DATABASE_ID)
    table_html = build_main_database_table(results, current_page=page_num, per_page=50)
    total_pages = math.ceil(len(results) / 50)
    return render_template("index.html", table=table_html, current_page=page_num, total_pages=total_pages)

# 브랜드별 상세 페이지 (sub.html)
@app.route("/sub")
def sub():
    brand_id = request.args.get("brand_id")
    page_content = fetch_page_content(brand_id) if brand_id else {"content": ["브랜드 상세 콘텐츠 없음"]}
    # 서브 데이터베이스 (필터링 로직을 추가할 수 있음)
    sub_table = fetch_sub_database(DATABASE_ID)
    return render_template("sub.html", brand_id=brand_id, content=page_content, table=sub_table)

# 특정 페이지 콘텐츠 가져오기
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