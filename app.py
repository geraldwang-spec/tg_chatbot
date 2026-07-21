"""
AI 聊天網頁版 — Streamlit
功能：角色設定、對話記憶、PDF 讀取、網路搜尋、網址內容讀取、台鐵時刻表查詢 (TDX)
使用者在側邊欄輸入自己的 API 金鑰，直接從瀏覽器呼叫 OpenRouter API。
部署方式：上傳到 GitHub，再連結到 Streamlit Community Cloud 免費部署。
"""

import io
import time
import requests
from datetime import datetime

import streamlit as st
from pypdf import PdfReader
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# ─────────────────────────────────────────────
# 頁面設定
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI 聊天助理",
    page_icon="🤖",
    layout="wide",
)

# ─────────────────────────────────────────────
# 常數
# ─────────────────────────────────────────────
OPENROUTER_BASE = "https://openrouter.ai/api/v1"
TDX_AUTH_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_TRA_BASE = "https://tdx.transportdata.tw/api/basic/v3/Rail/TRA"

DEFAULT_ROLE = "你是一個樂於助人的 AI 助理。"
MAX_PDF_CHARS = 15000
MAX_WEB_CHARS = 8000
SEARCH_RESULT_COUNT = 5
MAX_HISTORY_MESSAGES = 20
TRA_TIMETABLE_MAX_ROWS = 10

TRAIN_TYPE_NAMES = {
    "1": "太魯閣", "2": "普悠瑪", "3": "自強(3000)", "4": "自強(2000)",
    "5": "莒光", "6": "復興", "7": "區間", "8": "普快", "10": "區間快",
    "11": "新自強(3000)", "1131": "普快(專用)",
}

POPULAR_MODELS = [
    "openai/gpt-4o-mini",
    "openai/gpt-4o",
    "openai/o1-mini",
    "anthropic/claude-3-5-haiku",
    "anthropic/claude-3-5-sonnet",
    "google/gemini-flash-1.5",
    "google/gemini-pro-1.5",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
]

# ─────────────────────────────────────────────
# Session State 初始化
# ─────────────────────────────────────────────
def init_session():
    defaults = {
        "messages": [],
        "system_role": DEFAULT_ROLE,
        "pdf_info": None,
        "webpage_info": None,
        "tdx_token": None,
        "tdx_token_expires": 0,
        "tra_stations": None,
        "tra_stations_expires": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_session()

# ─────────────────────────────────────────────
# 工具函式（必須在 UI 之前定義）
# ─────────────────────────────────────────────

def extract_pdf_text(pdf_bytes: bytes) -> str:
    """從 PDF 擷取原生文字層"""
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages).strip()
    except Exception:
        return ""


def fetch_webpage_text(url: str):
    """抓取網頁純文字，回傳 (text, error_msg)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; StreamlitBot/1.0)"}
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg"]):
            tag.decompose()
        lines = [l.strip() for l in soup.get_text(separator="\n").splitlines()]
        text = "\n".join(l for l in lines if l)
        return text[:MAX_WEB_CHARS], None
    except Exception as e:
        return "", str(e)


def web_search_ddg(query: str) -> list:
    """DuckDuckGo 搜尋"""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=SEARCH_RESULT_COUNT))
    except Exception:
        return []


def build_system_prompt() -> str:
    """組合 system prompt（角色 + PDF + 網頁）"""
    parts = [st.session_state.system_role]
    pdf = st.session_state.pdf_info
    if pdf:
        text = pdf["text"][:MAX_PDF_CHARS]
        note = "\n（注意：PDF 內容過長，僅擷取前面部分）" if len(pdf["text"]) > MAX_PDF_CHARS else ""
        parts.append(
            f"以下是使用者上傳的 PDF 文件「{pdf['filename']}」的內容，"
            f"請根據這份文件的內容來回答使用者的問題。{note}\n"
            f"----- PDF 內容開始 -----\n{text}\n----- PDF 內容結束 -----"
        )
    web = st.session_state.webpage_info
    if web:
        text = web["text"][:MAX_WEB_CHARS]
        note = "\n（注意：網頁內容過長，僅擷取前面部分）" if len(web["text"]) > MAX_WEB_CHARS else ""
        parts.append(
            f"以下是網址「{web['url']}」的頁面內容，"
            f"請根據這份內容來回答使用者的問題。{note}\n"
            f"----- 網頁內容開始 -----\n{text}\n----- 網頁內容結束 -----"
        )
    return "\n\n".join(parts)


def call_openrouter(api_key: str, model: str, user_message: str) -> str:
    """呼叫 OpenRouter API，帶入歷史對話"""
    if not api_key:
        return "❌ 請在左側側邊欄輸入您的 OpenRouter API Key。"

    history = list(st.session_state.messages)
    history.append({"role": "user", "content": user_message})
    messages = [{"role": "system", "content": build_system_prompt()}] + history

    try:
        resp = requests.post(
            f"{OPENROUTER_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com",
                "X-Title": "AI Chat Assistant",
            },
            json={"model": model, "messages": messages, "max_tokens": 2000},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        return f"❌ API 錯誤 {resp.status_code}：{detail}"
    except Exception as e:
        return f"❌ 呼叫失敗：{e}"


# ── TDX 台鐵 ──

def _get_tdx_token(client_id: str, client_secret: str):
    """取得 TDX access token（帶 session 快取）"""
    now = time.time()
    if st.session_state.tdx_token and now < st.session_state.tdx_token_expires - 60:
        return st.session_state.tdx_token
    try:
        resp = requests.post(
            TDX_AUTH_URL,
            data={"grant_type": "client_credentials",
                  "client_id": client_id, "client_secret": client_secret},
            timeout=15,
        )
        resp.raise_for_status()
        result = resp.json()
        st.session_state.tdx_token = result["access_token"]
        st.session_state.tdx_token_expires = now + result.get("expires_in", 86400)
        return st.session_state.tdx_token
    except Exception:
        return None


def _get_tra_stations(token: str) -> list:
    """取得台鐵車站清單（帶 session 快取）"""
    now = time.time()
    if st.session_state.tra_stations and now < st.session_state.tra_stations_expires:
        return st.session_state.tra_stations
    try:
        resp = requests.get(
            f"{TDX_TRA_BASE}/Station?$format=JSON",
            headers={"authorization": f"Bearer {token}"}, timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
        stations = raw.get("Stations", raw) if isinstance(raw, dict) else raw
        st.session_state.tra_stations = stations
        st.session_state.tra_stations_expires = now + 86400
        return stations
    except Exception:
        return []


def _find_station(stations: list, name: str):
    target = name.strip().replace("台", "臺")
    for s in stations:
        sn = s.get("StationName", {}).get("Zh_tw", "")
        if sn.replace("台", "臺") == target:
            return s["StationID"], sn
    for s in stations:
        sn = s.get("StationName", {}).get("Zh_tw", "")
        if target in sn.replace("台", "臺"):
            return s["StationID"], sn
    return None


def query_train_timetable(client_id: str, client_secret: str,
                           from_name: str, to_name: str, date_str: str) -> str:
    """查詢台鐵時刻表，回傳格式化字串"""
    token = _get_tdx_token(client_id, client_secret)
    if not token:
        return "❌ TDX 認證失敗，請確認 Client ID / Secret 是否正確。"
    stations = _get_tra_stations(token)
    if not stations:
        return "❌ 無法取得車站清單。"
    from_match = _find_station(stations, from_name)
    to_match = _find_station(stations, to_name)
    if not from_match:
        return f"⚠️ 找不到出發站「{from_name}」，請確認站名。"
    if not to_match:
        return f"⚠️ 找不到到達站「{to_name}」，請確認站名。"
    from_id, from_official = from_match
    to_id, to_official = to_match
    try:
        resp = requests.get(
            f"{TDX_TRA_BASE}/DailyTrainTimetable/OD/{from_id}/to/{to_id}/{date_str}?$format=JSON",
            headers={"authorization": f"Bearer {token}"}, timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return f"❌ 查詢時刻表失敗：{e}"

    if isinstance(data, dict):
        rows = data.get("TrainTimetables", [])
        if not rows:
            for v in data.values():
                if isinstance(v, list):
                    rows = v
                    break
    elif isinstance(data, list):
        rows = data
    else:
        rows = []

    if not rows:
        return f"😥 查不到 {date_str} 從「{from_official}」到「{to_official}」的班次。"

    lines = [f"🚆 {date_str}｜{from_official} → {to_official}\n"]
    for row in rows[:TRA_TIMETABLE_MAX_ROWS]:
        train = row.get("TrainInfo", {})
        train_no = train.get("TrainNo", "?")
        type_code = str(train.get("TrainTypeID", ""))
        train_type = TRAIN_TYPE_NAMES.get(
            type_code, train.get("TrainTypeName", {}).get("Zh_tw", ""))
        stops = row.get("StopTimes", [])
        dep = stops[0]["DepartureTime"] if stops else "?"
        arr = stops[-1]["ArrivalTime"] if stops else "?"
        lines.append(f"🚉 {train_no}（{train_type}） {dep} → {arr}")
    if len(rows) > TRA_TIMETABLE_MAX_ROWS:
        lines.append(f"\n（共 {len(rows)} 班，僅顯示前 {TRA_TIMETABLE_MAX_ROWS} 筆）")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# 側邊欄：設定區
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("⚙️ 設定")

    st.subheader("🔑 API 金鑰")
    openrouter_key = st.text_input(
        "OpenRouter API Key",
        type="password",
        placeholder="sk-or-v1-...",
        help="從 https://openrouter.ai/keys 取得",
    )
    model_choice = st.selectbox("AI 模型", POPULAR_MODELS, index=0)

    st.divider()

    st.subheader("🎭 AI 角色設定")
    new_role = st.text_area(
        "系統提示詞（System Prompt）",
        value=st.session_state.system_role,
        height=100,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("套用角色", use_container_width=True):
            st.session_state.system_role = new_role
            st.session_state.messages = []
            st.success("已套用，對話已清除")
    with col2:
        if st.button("重置預設", use_container_width=True):
            st.session_state.system_role = DEFAULT_ROLE
            st.session_state.messages = []
            st.rerun()

    st.divider()

    st.subheader("📄 PDF 上傳")
    uploaded_pdf = st.file_uploader("上傳 PDF 檔案", type=["pdf"])
    if uploaded_pdf:
        if st.button("載入 PDF"):
            with st.spinner("讀取 PDF 中..."):
                pdf_text = extract_pdf_text(uploaded_pdf.read())
            if pdf_text:
                st.session_state.pdf_info = {"filename": uploaded_pdf.name, "text": pdf_text}
                st.session_state.messages = []
                st.success(f"✅ 已載入：{uploaded_pdf.name}（{len(pdf_text)} 字）")
            else:
                st.error("❌ 無法從此 PDF 擷取文字")
    if st.session_state.pdf_info:
        st.info(f"📄 已載入：{st.session_state.pdf_info['filename']}")
        if st.button("清除 PDF"):
            st.session_state.pdf_info = None
            st.session_state.messages = []
            st.rerun()

    st.divider()

    st.subheader("🌐 載入網頁")
    url_input = st.text_input("輸入網址", placeholder="https://example.com")
    if st.button("讀取網頁"):
        if not url_input:
            st.warning("請輸入網址")
        else:
            with st.spinner("讀取網頁中..."):
                web_text, err = fetch_webpage_text(url_input)
            if err:
                st.error(f"❌ {err}")
            elif web_text:
                st.session_state.webpage_info = {"url": url_input, "text": web_text}
                st.session_state.messages = []
                st.success(f"✅ 已讀取（{len(web_text)} 字）")
            else:
                st.warning("⚠️ 沒有擷取到文字內容")
    if st.session_state.webpage_info:
        st.info(f"🌐 已載入：{st.session_state.webpage_info['url'][:40]}...")
        if st.button("清除網頁"):
            st.session_state.webpage_info = None
            st.session_state.messages = []
            st.rerun()

    st.divider()

    st.subheader("🚆 台鐵時刻表")
    tdx_id = st.text_input("TDX Client ID", type="password")
    tdx_secret = st.text_input("TDX Client Secret", type="password")
    col_from, col_to = st.columns(2)
    with col_from:
        train_from = st.text_input("出發站", placeholder="台北")
    with col_to:
        train_to = st.text_input("到達站", placeholder="台中")
    train_date = st.date_input("日期", value=datetime.today())
    if st.button("查詢時刻表", use_container_width=True):
        if not tdx_id or not tdx_secret:
            st.warning("請輸入 TDX 金鑰")
        elif not train_from or not train_to:
            st.warning("請輸入出發站和到達站")
        else:
            with st.spinner("查詢中..."):
                train_result = query_train_timetable(
                    tdx_id, tdx_secret,
                    train_from, train_to,
                    train_date.strftime("%Y-%m-%d"),
                )
            st.info(train_result)

    st.divider()
    if st.button("🗑️ 清除所有對話", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# ─────────────────────────────────────────────
# 主介面：聊天區
# ─────────────────────────────────────────────
st.title("🤖 AI 聊天助理")
st.caption("支援 OpenRouter 所有模型 · PDF 讀取 · 網路搜尋 · 台鐵時刻表")

# 狀態標籤
status_parts = []
if st.session_state.pdf_info:
    status_parts.append(f"📄 PDF：{st.session_state.pdf_info['filename']}")
if st.session_state.webpage_info:
    status_parts.append(f"🌐 網頁：{st.session_state.webpage_info['url'][:30]}...")
if st.session_state.system_role != DEFAULT_ROLE:
    status_parts.append("🎭 自訂角色")
if status_parts:
    st.info("  ·  ".join(status_parts))

# 網路搜尋列
with st.expander("🔍 網路搜尋（搜尋後 AI 根據結果回答）"):
    search_col1, search_col2 = st.columns([4, 1])
    with search_col1:
        search_query = st.text_input(
            "搜尋關鍵字", label_visibility="collapsed",
            placeholder="例：台南 美食推薦", key="search_input",
        )
    with search_col2:
        do_search = st.button("搜尋並問 AI", use_container_width=True)

# 顯示對話歷史
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 網路搜尋執行
if do_search and search_query:
    if not openrouter_key:
        st.warning("請先在側邊欄輸入 OpenRouter API Key")
    else:
        with st.spinner("搜尋中..."):
            results = web_search_ddg(search_query)
        if not results:
            st.warning("😥 沒有找到相關的搜尋結果。")
        else:
            results_text = "\n\n".join(
                f"[{i+1}] 標題：{r.get('title', '')}\n"
                f"連結：{r.get('href', '')}\n"
                f"摘要：{r.get('body', '')}"
                for i, r in enumerate(results)
            )
            augmented = (
                f"請根據以下網路搜尋結果，回答使用者的問題：「{search_query}」\n"
                f"回答時請統整重點，並在文末列出參考來源連結。\n\n"
                f"----- 搜尋結果開始 -----\n{results_text}\n----- 搜尋結果結束 -----"
            )
            with st.chat_message("user"):
                st.markdown(f"🔍 搜尋：{search_query}")
            with st.chat_message("assistant"):
                with st.spinner("AI 分析中..."):
                    reply = call_openrouter(openrouter_key, model_choice, augmented)
                st.markdown(reply)
            st.session_state.messages.append({"role": "user", "content": f"🔍 搜尋：{search_query}"})
            st.session_state.messages.append({"role": "assistant", "content": reply})
            if len(st.session_state.messages) > MAX_HISTORY_MESSAGES:
                st.session_state.messages = st.session_state.messages[-MAX_HISTORY_MESSAGES:]
            st.rerun()

# 一般文字輸入
if user_input := st.chat_input("輸入訊息，按 Enter 送出..."):
    if not openrouter_key:
        st.warning("請先在左側側邊欄輸入您的 OpenRouter API Key。")
    else:
        with st.chat_message("user"):
            st.markdown(user_input)
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                reply = call_openrouter(openrouter_key, model_choice, user_input)
            st.markdown(reply)
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.session_state.messages.append({"role": "assistant", "content": reply})
        if len(st.session_state.messages) > MAX_HISTORY_MESSAGES:
            st.session_state.messages = st.session_state.messages[-MAX_HISTORY_MESSAGES:]
