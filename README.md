Multi-Functional Telegram AI Chatbot

[專案簡介]
本專案為一個基於 Python 與 python-telegram-bot 開發的多功能 AI 聊天機器人[cite: 1]。
整合 OpenRouter API、TDX 交通部 API、DuckDuckGo 搜尋與 PDF/OCR 辨識，提供一站式智慧對話與服務體驗[cite: 1]。

--------------------------------------------------------------------------------
【核心特色】
--------------------------------------------------------------------------------
1. 🎭 角色設定與對話記憶：自訂 System Prompt，滑動視窗保留最新 20 則對話記憶[cite: 1]。
2. 📄 PDF 與 OCR 讀取：原生文字層優先提取，掃描檔自動切換 Tesseract OCR 辨識[cite: 1]。
3. 🔎 即時網路搜尋：串接 DuckDuckGo 免金鑰搜尋，提供即時網路資訊[cite: 1]。
4. 🌐 指定網頁閱讀：解析網頁純文字並暫存，可持續針對網頁內容進行提問[cite: 1]。
5. 🚆 台鐵時刻表查詢：串接 TDX 官方 Open API，即時查詢起訖站車次資訊[cite: 1]。

--------------------------------------------------------------------------------
【技術棧 (Tech Stack)】
--------------------------------------------------------------------------------
- 程式語言：Python 3.10+
- 框架與異步處理：python-telegram-bot, asyncio, aiohttp[cite: 1]
- AI 模型介面：OpenRouter API[cite: 1]
- 文件解析與 OCR：pypdf, pytesseract (Tesseract OCR)[cite: 1]
- 外部資料源：TDX 運輸資料流通服務平臺, DuckDuckGo[cite: 1]

--------------------------------------------------------------------------------
【快速開始 (Quick Start)】
--------------------------------------------------------------------------------
1. 下載專案：
   git clone https://github.com/geraldwang-spec/tg_chatbot.git[cite: 1]
   cd tg_chatbot

2. 安裝依賴套件：
   pip install -r requirements.txt

3. 設定 .env 檔案（於根目錄建立）：
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   OPENROUTER_API_KEY=your_openrouter_api_key
   TDX_CLIENT_ID=your_tdx_client_id
   TDX_CLIENT_SECRET=your_tdx_client_secret

4. 啟動機器人：
   python main.py

--------------------------------------------------------------------------------
【系統控制指令手冊 (Command Protocol)】
--------------------------------------------------------------------------------
/setrole [提示詞]                  自訂助理人格 (System Prompt)，並同步重置上下文[cite: 1]
                                   範例：/setrole 你是一個幽默的科技顧問[cite: 1]

/search [關鍵字]                   強制啟動即時網路搜尋，整合 LLM 進行綜合解答[cite: 1]
                                   範例：/search 台北明日天氣預報[cite: 1]

/url [網址]                        解析外部網頁內容並暫存，可持續針對該內容提問[cite: 1]
                                   範例：/url https://example.com/news[cite: 1]

/train [起站] [到達站] [日期]      查詢起訖站台鐵時刻表，未填日期時預設為當日[cite: 1]
                                   範例：/train 台北 台中 2026-07-20[cite: 1]

/clearpdf                          清除當前會話暫存的 PDF 內容與上下文記憶[cite: 1]

--------------------------------------------------------------------------------
【未來展望 (Roadmap)】
--------------------------------------------------------------------------------
- 導入持久化儲存（SQLite/PostgreSQL），取代記憶體字典[cite: 1]。
- 擴充 TDX 整合範圍：高鐵、市區公車與捷運[cite: 1]。
- 加入使用者身分驗證與 API 調用頻率管控[cite: 1]。
- 站名比對支援模糊校正與容錯機制[cite: 1]。

-------------------------------------------------------------------------------
專案網址
-------------------------------------------------------------------------------
https://geraldwang-spec.github.io/tg_chatboot
