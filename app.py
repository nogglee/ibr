from flask import Flask, render_template, jsonify, request
import requests
import math
import json

app = Flask(__name__)

# 노션 API 설정
NOTION_API_KEY = "secret_IVUUMjyv15f1rUKFj0PAKrEzWr6LzHJqKRrnmH1gfrF"  # 본인의 노션 API 키 입력
DATABASE_ID = "1a16f73a586080368e0dd54311df4886"  # 본인의 데이터베이스 ID 입력
HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

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
        
        # 🔍 각 페이지의 속성 확인 (ID 값만 출력)
        for page in data.get("results", []):
            properties = page.get("properties", {})
            page_id = page.get("id", "N/A")  # 페이지 자체의 Notion ID
            unique_id = properties.get("ID", {}).get("unique_id", "N/A")  # ✅ unique_id 가져오기
            print(f"🔍 페이지 Notion ID: {page_id}, 브랜드 ID: {unique_id}")
        
        if not data.get("has_more"):
            break
        payload["start_cursor"] = data.get("next_cursor")
    
    return results

def build_main_database_table(results, current_page=1, per_page=50):
    start = (current_page - 1) * per_page
    end = start + per_page
    sliced = results[start:end]
    
    # (컬럼명, 프로퍼티 타입) – 순서대로 정의
    columns = [
        ("ID", "unique_id"),  # ✅ 브랜드 ID 추가
        ("브랜드", "title"),
        ("브랜드정보", "rich_text"),
        ("채택현황", "select"),
        ("카테고리", "multi_select"),
        ("메인아이템", "multi_select"),
        ("브랜드홈페이지", "url"),
        ("우선순위", "select"),
        ("CJ 담당자", "rich_text"),
        ("IBR담당자", "people"),
        ("업무진행현황", "status"),
        ("글로벌담당자", "people"),
        ("수입방법", "select"),
        ("제안사", "select"),
        ("제안일자", "date"),
        ("주요입점", "rich_text"),
        ("국가", "select"),
        ("생성일시", "create_date")
    ]
    
    html = "<table border='1'><tr>"
    for col_name, _ in columns:
        html += f"<th>{col_name}</th>"
    html += "</tr>"
    
    for page in sliced:
        properties = page.get("properties", {})
        notion_page_id = page.get("id")  # 페이지의 Notion ID 가져오기
        row = "<tr>"
        
        for col_name, col_type in columns:
            value = ""
            if col_type == "unique_id":  # ID 구조: {"prefix": "CJ", "number": 90}
                id_data = properties.get(col_name, {}).get("unique_id", {})
                prefix = id_data.get("prefix", "")
                num = id_data.get("number", "")
                value = f"{prefix}-{num}" if prefix or num else ""
                brand_id = value
            
            elif col_type == "multi_select":
                items = properties.get(col_name, {}).get("multi_select", [])
                value = ", ".join(item.get("name", "") for item in items) if items else ""
            
            elif col_type == "title":
                items = properties.get(col_name, {}).get("title", [])
                value = items[0].get("plain_text", "") if items else ""
                if col_name == "브랜드":
                    # 브랜드명을 클릭하면 notion_page_id로 사이드바 로딩 (page ID 사용)
                    value = f'<a href="#" onclick="loadPageContent(\'{notion_page_id}\')">{value}</a>'
            
            elif col_type == "rich_text":
                items = properties.get(col_name, {}).get("rich_text", [])
                value = items[0].get("plain_text", "") if items else ""
            
            elif col_type == "select":
                sel = properties.get(col_name, {}).get("select", {})
                value = sel.get("name", "") if sel else ""
            
            elif col_type == "text":
                value = properties.get(col_name, {}).get("text", "") or ""

            elif col_type == "status":
                sel = properties.get(col_name, {}).get("status", {}) or ""
                value = sel.get("name", "") if sel else ""
            
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

# 📌 특정 브랜드 페이지 콘텐츠 가져오기
def fetch_page_content(page_id):
    url = f"https://api.notion.com/v1/blocks/{page_id}/children"
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return {"content": ["페이지 콘텐츠를 불러오지 못했습니다."], "child_databases": []}

    data = response.json()
    page_content = []
    child_databases = []  # 페이지 내 데이터베이스 블록 IDs 저장

    for block in data.get("results", []):
        block_type = block.get("type")
        block_id = block.get("id")
        
        # 자식 데이터베이스 블록 찾기
        if block_type == "child_database":
            print(f"📊 자식 데이터베이스 발견: {block_id}")
            child_databases.append(block_id)
            continue
            
        content_text = ""
        if block_type == "paragraph":
            texts = block.get("paragraph", {}).get("rich_text", [])
            content_text = "".join(t.get("plain_text", "") for t in texts)
        elif block_type.startswith("heading"):
            texts = block.get(block_type, {}).get("rich_text", [])
            heading_size = block_type[-1]
            content_text = f"<h{heading_size}>" + "".join(t.get("plain_text", "") for t in texts) + f"</h{heading_size}>"

        if content_text:
            page_content.append(content_text)

    return {"content": page_content, "child_databases": child_databases}

# 📌 자식 데이터베이스의 콘텐츠 가져오기
def fetch_child_database_content(database_id):
    """
    자식 DB에서 '담당자', '업무진행현황', '날짜', '로그'만 고정 컬럼으로 파싱하고,
    완료 상태(complete_statuses)인 항목만 출력.
    """
    complete_statuses = ["CJ 최종 점검", "PO전달 to IBR", "CJ - 본 물량 입고", "CJ - 본 물량 수입", "판매시작"]
    
    # 1) DB 정보 (생략 가능)
    db_url = f"https://api.notion.com/v1/databases/{database_id}"
    info_res = requests.get(db_url, headers=HEADERS)
    if info_res.status_code != 200:
        return "<p>데이터베이스 정보를 불러오지 못했습니다.</p>"
    
    # 2) DB 쿼리
    query_url = f"https://api.notion.com/v1/databases/{database_id}/query"
    resp = requests.post(query_url, headers=HEADERS, json={})
    if resp.status_code != 200:
        return "<p>데이터베이스 콘텐츠를 불러오지 못했습니다.</p>"
    
    data = resp.json()
    results = data.get("results", [])
    if not results:
        return "<p>데이터베이스에 항목이 없습니다.</p>"
    
    # 3) 고정 컬럼 테이블
    table_html = "<table border='1'><tr>"
    table_html += "<th>담당자</th><th>업무진행현황</th><th>날짜</th><th>로그</th>"
    table_html += "</tr>"
    
    for row in results:
        props = row.get("properties", {})
        
        # 상태값
        st_obj = props.get("업무진행현황", {}).get("status", {})
        st_name = st_obj.get("name", "N/A")
        if st_name not in complete_statuses:
            continue
        
        # 담당자
        ppl = props.get("담당자", {}).get("people", [])
        dname = ", ".join(x.get("name", "") for x in ppl) if ppl else ""
        
        # 날짜
        day_obj = props.get("날짜", {}).get("date", {})
        day_val = day_obj.get("start", "N/A") if day_obj else ""
        
        # 로그
        log_arr = props.get("로그", {}).get("rich_text", [])
        log_val = log_arr[0].get("plain_text", "N/A") if log_arr else ""
        
        table_html += f"<tr><td>{dname}</td><td>{st_name}</td><td>{day_val}</td><td>{log_val}</td></tr>"
    
    table_html += "</table>"
    return table_html

@app.route("/")
def index():
    page_num = int(request.args.get("page", 1))
    results = fetch_all_main_database(DATABASE_ID)
    table_html = build_main_database_table(results, current_page=page_num, per_page=50)
    total_pages = math.ceil(len(results) / 50)
    return render_template("index.html", table=table_html, current_page=page_num, total_pages=total_pages)

@app.route("/get-brand-content/<page_id>")
def get_brand_content(page_id):
    print(f"브랜드 콘텐츠 요청: {page_id}")
    
    # 📌 브랜드 페이지의 콘텐츠와 자식 데이터베이스 ID 가져오기
    page_data = fetch_page_content(page_id)
    
    # 자식 데이터베이스가 있는 경우 첫 번째 데이터베이스의 콘텐츠 가져오기
    sub_db_content = "<p>서브 데이터베이스가 없습니다.</p>"
    if page_data["child_databases"]:
        first_db_id = page_data["child_databases"][0]
        sub_db_content = fetch_child_database_content(first_db_id)

    return jsonify({
        "content": page_data["content"],
        "sub_database": sub_db_content
    })

@app.errorhandler(404)
def page_not_found(e):
    return jsonify({"error": "Not Found"}), 404

@app.errorhandler(500)
def internal_server_error(e):
    return jsonify({"error": "Internal Server Error"}), 500

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=True)