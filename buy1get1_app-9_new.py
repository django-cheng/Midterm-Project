"""
全聯福利中心 特價商品瀏覽器 v2
六個專區：本檔必買 / 抗漲專區 / 憑卡買一送一 / 卡友特惠價 / 買一送一大集合 / 天天省更多
執行：python buy1get1_app.py
套件：pip install requests beautifulsoup4
"""

import re
import threading
import webbrowser
import tkinter as tk
import customtkinter as ctk
import requests
from tkinter import ttk, font as tkfont
from urllib.parse import quote
from bs4 import BeautifulSoup


# ── 六專區定義 ──────────────────────────────────────────
BASE = "https://www.pxmart.com.tw"
SECTIONS = [
    {"label": "本檔必買",     "icon": "🛒", "url": BASE + "/campaign/life-will/best-buy/" + quote("本檔必買"),     "color": "#1d45ee", "bg": "#fff0f0"},
    {"label": "抗漲專區",     "icon": "📉", "url": BASE + "/campaign/life-will/best-buy/" + quote("抗漲專區"),     "color": "#0077cc", "bg": "#f0f6ff"},
    {"label": "憑卡買一送一", "icon": "💳", "url": BASE + "/campaign/life-will/best-buy/" + quote("憑卡買一送一"), "color": "#6a0dad", "bg": "#f8f0ff"},
    {"label": "卡友特惠價",   "icon": "🎫", "url": BASE + "/campaign/life-will/best-buy/" + quote("卡友特惠價"),   "color": "#b06000", "bg": "#fff8ec"},
    {"label": "買一送一大集合","icon": "🎁", "url": BASE + "/campaign/life-will/best-buy/" + quote("買一送一大集合"),"color": "#1b7a3e", "bg": "#f0fff5"},
    {"label": "天天省更多",   "icon": "💰", "url": BASE + "/campaign/life-will/best-buy/" + quote("天天省更多"),   "color": "#ad1457", "bg": "#fff0f5"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9",
}

# ── 爬蟲 ────────────────────────────────────────────────
def scrape_section(url: str):
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # 一、活動期間（完整抓取「開始日期 ~ 結束日期」）
    sale_period = "活動期間請見官網"
    full_text = soup.get_text(separator=" ")
    m_period = re.search(
        r"(\d{4}-\d{2}-\d{2})\s*~\s*(\d{4}-\d{2}-\d{2})", full_text
    )
    if m_period:
        sale_period = f"{m_period.group(1)} ~ {m_period.group(2)}"
    else:
        date_span = soup.find("span", class_=re.compile(r"dateText"))
        if date_span:
            span_text = date_span.get_text(strip=True)
            dates = re.findall(r"\d{4}-\d{2}-\d{2}", span_text)
            if len(dates) >= 2:
                sale_period = f"{dates[0]} ~ {dates[1]}"
            elif len(dates) == 1:
                sale_period = f"{dates[0]} ~ (請見官網)"

    # 二、商品清單
    items = []
    for h5 in soup.find_all("h5"):
        name = h5.get_text(strip=True)
        if not name:
            continue
        container = h5.parent
        if not container:
            continue

        card_ul = container.find("ul", class_=re.compile(r"Card_card-list"))
        lis = card_ul.find_all("li") if card_ul else container.find_all("li")

        detail_parts = []
        card_list = []
        for li in lis:
            t = li.get_text(strip=True)
            if not t:
                continue
            detail_parts.append(t)
            card_list.append(t)

        price = None
        price_container = container.find("div", class_=re.compile(r"Card_card-priceContainer"))
        if price_container:
            price_tag = price_container.find("p", class_=re.compile(r"Card_card-productPrice"))
            if price_tag:
                m = re.search(r"(\d[\d,]*)", price_tag.get_text(strip=True).replace(",", ""))
                if m:
                    price = int(m.group(1))

        detail_str = " | ".join(detail_parts)

        items.append({
            "name":      name,
            "price":     price,
            "detail":    detail_str,
            "card_list": card_list,
            "category":  _guess_category(name),
        })

    return items, sale_period

# ── 類別推測 ────────────────────────────────────────────
_CATS = {
    "☕ 咖啡沖調":  ["咖啡", "茶包", "燕麥片", "奶粉", "麥片", "可可", "藜麥", "麥茶"],
    "🥤 飲料":      ["礦泉水", "飲料", "燕窩", "牛乳", "保久乳", "能量飲", "氣泡水",
                     "鹼性離子水", "醇茶", "烏龍茶", "綠茶", "紅茶", "銀耳", "四季春",
                      "可樂", "汽水", "燕麥", "啤酒"],
    "🍜 食品":      ["麵", "醬", "醋", "湯", "泡菜", "米果", "鍋巴", "年糕",
                     "玉米", "雞肉鬆", "水餃", "優格", "玄米油", "果油",
                     "鮪魚", "海苔", "洋芋片", "布朗尼", "蔥抓餅", "鵝油", "米",
                      "餅乾", "雪糕", "口香糖"],
    "🥩 生鮮":      ["鱸魚", "鯛", "豬", "雞翅", "鮮", "小黃瓜", "菇", "蔬菜",
                     "排骨", "牛", "羊", "魚", "肉"],
    "🧴 個人清潔":  ["洗髮", "沐浴", "漱口", "牙膏", "牙刷", "牙線", "護墊",
                     "衛生棉", "染髮", "護膚", "面膜", "植漱口"],
    "🧹 家用清潔":  ["洗衣", "清潔", "魔術靈", "吸油紙", "密封袋", "洗潔精",
                     "消臭", "防臭", "洗衣粉", "洗衣精", "OP袋"],
    "🦟 防蚊驅蟲":  ["防蚊", "電蚊香", "驅蟲", "派卡瑞丁"],
    "👶 嬰兒用品":  ["尿褲", "嬰兒", "寶寶"],
    "💊 保健營養":  ["葡萄糖胺", "乳清", "益生菌", "人蔘", "靈芝", "維他命",
                     "雞精", "滋補", "配方", "保健", "膠原", "乳鐵蛋白"],
    "🏠 居家生活":  ["香氛", "芳香", "除濕", "廚房", "衛生紙", "抽取"],
}
def _guess_category(name: str):
    for cat, kws in _CATS.items():
        for kw in kws:
            if kw in name:
                return cat
    return "📦 其他"


# ── 主視窗 ──────────────────────────────────────────────
class PxmartApp(ctk.CTk):
    # 配色
    C_BG      = "#f5f6fa"
    C_HDR     = "#1d45ee"
    C_SIDEBAR = "#ffffff"
    C_PANEL   = "#ffffff"
    C_BORDER  = "#e0e0e0"
    C_TEXT    = "#1a1a2e"
    C_MUTE    = "#888888"
    C_ROW_ODD = "#f9f9fb"
    C_ROW_EVN = "#ffffff"
    C_SEL     = "#1d45ee"

    def __init__(self):
        super().__init__()
        self.title("全聯快速GO")
        self.geometry("1100x680")
        self.minsize(860, 520)
        self.configure(fg_color=self.C_BG)

        self._cache: dict[int, list[dict]] = {}
        self._periods: dict[int, str] = {}
        self._current_tab = 0
        self._filtered: list[dict] = []
        self._selected_item: dict | None = None

        self._build_ui()
        self._load_tab(0)

    # ── 整體版面 ────────────────────────────────────────
    def _build_ui(self):
        # ── 頂部 header ──
        hdr = ctk.CTkFrame(self, fg_color=self.C_HDR, height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)


        title_frame = ctk.CTkFrame(hdr, fg_color=self.C_HDR)
        title_frame.pack(side="left", pady=8)
        ctk.CTkLabel(title_frame, text="  全聯快速GO  ",
                 font=("微軟正黑體", 22, "bold"),
                 fg_color=self.C_HDR, text_color="white").pack(anchor="w")

        self._period_var = tk.StringVar(value="")
        ctk.CTkLabel(hdr, textvariable=self._period_var,
                 font=("微軟正黑體", 10),
                 fg_color=self.C_HDR, text_color="#ffcccc").pack(side="right", padx=20)

        # ── 左側分頁導覽 ──
        outer = ctk.CTkFrame(self, fg_color=self.C_BG)
        outer.pack(fill="both", expand=True)

        sidebar = ctk.CTkFrame(outer, fg_color=self.C_SIDEBAR, width=148,
                           border_color=self.C_BORDER,
                           border_width=1)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="專區選擇",
                 font=("微軟正黑體", 9, "bold"),
                 fg_color=self.C_SIDEBAR, text_color=self.C_MUTE).pack(pady=(14, 4), padx=14, anchor="w")

        self._tab_btns: list[ctk.CTkFrame] = []
        for i, sec in enumerate(SECTIONS):
            f = ctk.CTkFrame(sidebar, fg_color=self.C_SIDEBAR, cursor="hand2")
            f.pack(fill="x", padx=6, pady=2)

            icon_lbl = ctk.CTkLabel(f, text=sec["icon"],
                                font=("微軟正黑體", 13),
                                fg_color=self.C_SIDEBAR, text_color=sec["color"],
                                width=2)
            icon_lbl.pack(side="left", padx=(6, 4), pady=6)

            text_lbl = ctk.CTkLabel(f, text=sec["label"],
                                font=("微軟正黑體", 10),
                                fg_color=self.C_SIDEBAR, text_color=self.C_TEXT,
                                anchor="w")
            text_lbl.pack(side="left", fill="x", expand=True)

            # 計數標籤
            count_lbl = ctk.CTkLabel(f, text="",
                                 font=("微軟正黑體", 8),
                                 fg_color=self.C_SIDEBAR, text_color=self.C_MUTE)
            count_lbl.pack(side="right", padx=6)

            for widget in (f, icon_lbl, text_lbl, count_lbl):
                widget.bind("<Button-1>", lambda e, idx=i: self._switch_tab(idx))
                widget.bind("<Enter>",    lambda e, fr=f, idx=i: self._tab_hover(fr, idx, True))
                widget.bind("<Leave>",    lambda e, fr=f, idx=i: self._tab_hover(fr, idx, False))

            f._icon  = icon_lbl
            f._text  = text_lbl
            f._count = count_lbl
            self._tab_btns.append(f)

        # ── 右側主區域 ──
        main = ctk.CTkFrame(outer, fg_color=self.C_BG)
        main.pack(side="left", fill="both", expand=True)

        # 搜尋列
        toolbar = ctk.CTkFrame(main, fg_color=self.C_PANEL,
                           border_color=self.C_BORDER,
                           border_width=1)
        toolbar.pack(fill="x", padx=10, pady=(10, 0))

        ctk.CTkLabel(toolbar, text="🔍",
                 font=("微軟正黑體", 12),
                 fg_color=self.C_PANEL, text_color=self.C_MUTE).pack(side="left", padx=(10, 4), pady=8)
        self._q = tk.StringVar()
        self._q.trace_add("write", lambda *_: self._refresh_table())
        search_entry = ctk.CTkEntry(toolbar, textvariable=self._q,
                            border_width=1,
                            width=200, 
                            height=30)
        search_entry.pack(side="left", pady=8, padx=(0, 12))

        ctk.CTkFrame(toolbar, fg_color=self.C_BORDER, width=1).pack(side="left", fill="y", pady=6)

        # 類別列
        ctk.CTkLabel(toolbar, text="類別",
                 font=("微軟正黑體", 9), fg_color=self.C_PANEL,
                 text_color=self.C_MUTE).pack(side="left", padx=(12, 4))
        self._cat_var = tk.StringVar(value="全部")
        self._cat_cb = ttk.Combobox(toolbar, textvariable=self._cat_var,
                                    state="readonly",
                                    font=("微軟正黑體", 10), width=13)
        self._cat_cb["values"] = ["全部"]
        self._cat_cb.pack(side="left", padx=(0, 12), pady=6)
        self._cat_cb.bind("<<ComboboxSelected>>", lambda *_: self._refresh_table())
        ctk.CTkFrame(toolbar, fg_color=self.C_BORDER, width=1).pack(side="left", fill="y", pady=6)

        # 排序列
        ctk.CTkLabel(toolbar, text="排序",
                 font=("微軟正黑體", 9), fg_color=self.C_PANEL,
                 text_color=self.C_MUTE).pack(side="left", padx=(12, 4))
        self._sort_var = tk.StringVar(value="價格↑")
        ttk.Combobox(toolbar, textvariable=self._sort_var,
                     state="readonly",
                     font=("微軟正黑體", 10), width=7,
                     values=["價格↑", "價格↓", "類別↓","名稱↓"]).pack(
            side="left", padx=(0, 12), pady=6)
        self._sort_var.trace_add("write", lambda *_: self._refresh_table())

        self._count_var = tk.StringVar(value="")
        ctk.CTkLabel(toolbar, textvariable=self._count_var,
                 font=("微軟正黑體", 9), fg_color=self.C_PANEL,
                 text_color=self.C_MUTE).pack(side="left", padx=8)

        reload_btn = ctk.CTkButton(toolbar, text="↺  重新整理",
                           font=("微軟正黑體", 11),
                           fg_color=self.C_HDR,
                           text_color="white",
                           width=100, height=32,
                           cursor="hand2",
                           command=self._reload_current)
        reload_btn.pack(side="right", padx=10, pady=6)

        # 表格 + 詳情
        content = ctk.CTkFrame(main, fg_color=self.C_BG)
        content.pack(fill="both", expand=True, padx=10, pady=8)

        # 表格
        table_frame = ctk.CTkFrame(content, fg_color=self.C_PANEL,
                               border_color=self.C_BORDER,
                               border_width=1)
        table_frame.pack(side="left", fill="both", expand=True)

        cols = ("#", "商品名稱", "類別", "特價", "優惠說明")
        self._tree = ttk.Treeview(table_frame, columns=cols,
                                  show="headings", selectmode="browse")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("PX.Treeview",
                        background=self.C_ROW_EVN,
                        foreground=self.C_TEXT,
                        rowheight=30,
                        fieldbackground=self.C_ROW_EVN,
                        font=("微軟正黑體", 10),
                        borderwidth=0)
        style.configure("PX.Treeview.Heading",
                        background="#f0f0f4",
                        foreground=self.C_TEXT,
                        font=("微軟正黑體", 9, "bold"),
                        borderwidth=0)
        style.map("PX.Treeview",
                  background=[("selected", "#fff0f0")],
                  foreground=[("selected", "#c0001f")])
        self._tree.configure(style="PX.Treeview")

        col_cfg = {
            "#":     (38,  "center"),
            "商品名稱": (340, "w"),
            "類別":   (110, "center"),
            "特價":   (80,  "center"),
            "優惠說明": (280, "w"),
        }
        for c, (w, anchor) in col_cfg.items():
            self._tree.heading(c, text=c)
            self._tree.column(c, width=w, anchor=anchor,
                              stretch=(c == "商品名稱"))

        self._tree.tag_configure("odd",      background=self.C_ROW_ODD,  foreground=self.C_TEXT)
        self._tree.tag_configure("even",     background=self.C_ROW_EVN,  foreground=self.C_TEXT)
        self._tree.tag_configure("hot",      background="#fff8f0",       foreground="#c05000")
        self._tree.tag_configure("hot_odd",  background="#fff3e8",       foreground="#c05000")

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscroll=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>",         lambda e: self._open_browser())

        # 右側詳情卡片
        detail = ctk.CTkFrame(content, fg_color=self.C_PANEL, width=220,
                          border_color=self.C_BORDER,
                          border_width=1)
        detail.pack(side="right", fill="y", padx=(8, 0))
        detail.pack_propagate(False)

        # 專區色條
        self._detail_bar = ctk.CTkFrame(detail, fg_color=self.C_HDR, height=4)
        self._detail_bar.pack(fill="x")

        ctk.CTkLabel(detail, text="商品詳情",
                 font=("微軟正黑體", 11, "bold"),
                 fg_color=self.C_PANEL, text_color=self.C_TEXT).pack(pady=(12, 4), padx=14, anchor="w")
        ctk.CTkFrame(detail, fg_color=self.C_BORDER, height=1).pack(fill="x", padx=14)

        self._d_name = ctk.CTkLabel(detail, text="← 點選左側商品",
                                wraplength=192,
                                font=("微軟正黑體", 10, "bold"),
                                fg_color=self.C_PANEL, text_color=self.C_TEXT,
                                justify="left", anchor="w")
        self._d_name.pack(fill="x", padx=14, pady=(10, 2))

        self._d_cat = ctk.CTkLabel(detail, text="",
                               font=("微軟正黑體", 9),
                               fg_color=self.C_PANEL, text_color=self.C_MUTE, anchor="w")
        self._d_cat.pack(fill="x", padx=14, pady=(0, 6))

        # 價格區塊
        price_box = ctk.CTkFrame(detail, fg_color="#fafafa",
                             border_color=self.C_BORDER,
                             border_width=1)
        price_box.pack(fill="x", padx=14, pady=4)

        self._d_price = ctk.CTkLabel(price_box, text="",
                                 font=("微軟正黑體", 10),
                                 fg_color="#fafafa", text_color=self.C_MUTE, anchor="w")
        self._d_price.pack(fill="x", padx=10, pady=(8, 8))

        self._d_detail = ctk.CTkLabel(detail, text="",
                                  wraplength=192,
                                  font=("微軟正黑體", 9),
                                  fg_color=self.C_PANEL, text_color=self.C_MUTE,
                                  justify="left", anchor="nw")
        self._d_detail.pack(fill="x", padx=14, pady=8)

        ctk.CTkFrame(detail, fg_color=self.C_BORDER, height=1).pack(fill="x", padx=14)

        self._d_period = ctk.CTkLabel(detail, text="",
                                  font=("微軟正黑體", 9),
                                  fg_color=self.C_PANEL, text_color="#1b7a3e", anchor="w")
        self._d_period.pack(fill="x", padx=14, pady=8)

        self._open_btn = ctk.CTkButton(
            detail, text="全聯購物官網",
            font=("微軟正黑體", 10, "bold"),
            fg_color=self.C_HDR, text_color="white",
            width=140, height=35, cursor="hand2",
            state="disabled",
            command=self._open_browser)
        self._open_btn.pack(fill="x", padx=14, pady=(0, 14))

        # 底部狀態列
        footer = ctk.CTkFrame(self, fg_color="#eeeeee",
                          border_color=self.C_BORDER,
                          border_width=1, height=24)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)
        self._status_var = tk.StringVar(value="啟動中，正在載入資料...")
        ctk.CTkLabel(footer, textvariable=self._status_var,
                 font=("微軟正黑體", 9),
                 fg_color="#eeeeee", text_color="#999").pack(side="left", padx=12, pady=3)

    # ── 分頁切換 ────────────────────────────────────────
    def _switch_tab(self, idx: int):
        self._current_tab = idx
        self._highlight_tab(idx)
        self._q.set("")
        self._cat_var.set("全部")
        self._detail_bar.configure(fg_color=SECTIONS[idx]["color"])
        self._open_btn.configure(fg_color=SECTIONS[idx]["color"])

        if idx in self._cache:
            self._on_tab_loaded(idx)
        else:
            for row in self._tree.get_children():
                self._tree.delete(row)
            self._status_var.set(
                f"正在載入「{SECTIONS[idx]['icon']} {SECTIONS[idx]['label']}」...")
            self._period_var.set("")
            self._load_tab(idx)

    def _highlight_tab(self, idx: int):
        for i, f in enumerate(self._tab_btns):
            sec = SECTIONS[i]
            if i == idx:
                f.configure(fg_color=sec["bg"],
                         border_color=sec["color"],
                         border_width=2)
                f._icon.configure(fg_color=sec["bg"])
                f._text.configure(fg_color=sec["bg"],
                               text_color=sec["color"],
                               font=("微軟正黑體", 10, "bold"))
                f._count.configure(fg_color=sec["bg"])
            else:
                f.configure(fg_color=self.C_SIDEBAR,
                         border_width=0)
                f._icon.configure(fg_color=self.C_SIDEBAR)
                f._text.configure(fg_color=self.C_SIDEBAR,
                               text_color=self.C_TEXT,
                               font=("微軟正黑體", 10))
                f._count.configure(fg_color=self.C_SIDEBAR)

    def _tab_hover(self, fr, idx, entering):
        if idx == self._current_tab:
            return
        fr.configure(fg_color="#f5f5f5" if entering else self.C_SIDEBAR)
        fr._icon.configure(fg_color="#f5f5f5" if entering else self.C_SIDEBAR)
        fr._text.configure(fg_color="#f5f5f5" if entering else self.C_SIDEBAR)
        fr._count.configure(fg_color="#f5f5f5" if entering else self.C_SIDEBAR)

    # ── 資料載入 ────────────────────────────────────────
    def _load_tab(self, idx: int):
        self._highlight_tab(idx)
        threading.Thread(target=self._fetch_thread, args=(idx,), daemon=True).start()

    def _fetch_thread(self, idx: int):
        try:
            items, period = scrape_section(SECTIONS[idx]["url"])
            self._cache[idx] = items
            self._periods[idx] = period
            self.after(0, lambda: self._on_tab_loaded(idx))
        except Exception as e:
            self.after(0, lambda: self._status_var.set(f"載入失敗：{e}"))

    def _on_tab_loaded(self, idx: int):
        if idx != self._current_tab:
            return
        period = self._periods.get(idx, "")
        self._period_var.set(f"{period}" if period else "")
        # 更新側邊欄計數
        n = len(self._cache.get(idx, []))
        if idx < len(self._tab_btns):
            self._tab_btns[idx]._count.configure(
                text=str(n), text_color=SECTIONS[idx]["color"])
        self._update_cat_menu(idx)
        self._refresh_table()
        self._status_var.set(
            f"「{SECTIONS[idx]['label']}」共 {n} 項 ")

    def _reload_current(self):
        idx = self._current_tab
        self._cache.pop(idx, None)
        for row in self._tree.get_children():
            self._tree.delete(row)
        self._status_var.set("重新載入中...")
        self._load_tab(idx)

    # ── 類別選單 ────────────────────────────────────────
    def _update_cat_menu(self, idx: int):
        items = self._cache.get(idx, [])
        cats = sorted(set(it["category"] for it in items))
        self._cat_cb["values"] = ["全部"] + cats
        self._cat_var.set("全部")

    # ── 表格刷新 ────────────────────────────────────────
    def _refresh_table(self):
        idx   = self._current_tab
        items = self._cache.get(idx, [])
        q     = self._q.get().strip().lower()
        cat   = self._cat_var.get()
        srt   = self._sort_var.get()

        data = [
            it for it in items
            if (not q or q in it["name"].lower())
            and (cat == "全部" or it["category"] == cat)
        ]
        if srt == "價格↑":
            data.sort(key=lambda x: x["price"] or 0)
        elif srt == "價格↓":
            data.sort(key=lambda x: x["price"] or 0, reverse=True)
        elif srt == "類別↓":
            data.sort(key=lambda x: x["category"])
        else:
            data.sort(key=lambda x: x["name"])

        for row in self._tree.get_children():
            self._tree.delete(row)

        for i, it in enumerate(data, 1):
            price_str = f"${it['price']}" if it["price"] else "—"
            tag = "odd" if i % 2 else "even"

            self._tree.insert(
                "", "end", iid=str(i - 1), tags=(tag,),
                values=(i, it["name"], it["category"],
                        price_str, it["detail"]),
            )

        self._filtered = data
        total = len(self._cache.get(idx, []))
        self._count_var.set(f"顯示 {len(data)} / {total} 筆")

    # ── 選取商品 ────────────────────────────────────────
    def _on_select(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        it     = self._filtered[int(sel[0])]
        self._selected_item = it
        period = self._periods.get(self._current_tab, "")
        sec    = SECTIONS[self._current_tab]

        self._d_name.configure(text=it["name"])
        self._d_cat.configure(text=it["category"])
        self._d_price.configure(
            text=f"特價：${it['price']}" if it["price"] else "特價：—")
        self._d_detail.configure(text=it["detail"])
        self._d_period.configure(
            text=f"活動期間\n{period}" if period else "")
        self._open_btn.configure(state="normal", fg_color=sec["color"])

    # ── 自動搜尋並點擊第一項商品 ─────────────────────────
    def _open_browser(self):
        name = self._selected_item["name"] if self._selected_item else ""
        if not name:
            return

        self._status_var.set(f"正在開啟瀏覽器搜尋：{name}...")
    
        threading.Thread(
            target=self._selenium_flow,
            args=(name,),
            daemon=True
        ).start()

    def _selenium_flow(self, name: str):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        try:
            import chromedriver_autoinstaller
            chromedriver_autoinstaller.install()
        except Exception:
            pass

        opts = Options()
        opts.add_argument("--start-maximized")
        driver = webdriver.Chrome(options=opts)
        wait   = WebDriverWait(driver, 15)

        try:
            # ── 步驟一：開啟搜尋頁 ──
            driver.get("https://shop.pxgo.com.tw/hourArrive/search")
            self.after(0, lambda: self._status_var.set("步驟 1/3：已開啟搜尋頁..."))

            # ── 步驟二：找到 input 輸入商品名稱並送出 ──
            search_input = wait.until(
                EC.presence_of_element_located((
                    By.CSS_SELECTOR,
                    "div.relative.inline-flex.items-center.w-full input"
                ))
            )
            search_input.clear()
            search_input.send_keys(name)
            self.after(0, lambda: self._status_var.set(f"步驟 2/3：已輸入「{name}」，送出搜尋..."))

            # 點擊搜尋結果連結（href 帶 q=商品名稱）
            encoded = quote(name)
            search_link = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    f'a[href*="hourArrive/search/result"]'
                ))
            )
            search_link.click()

            # ── 步驟三：等待結果頁，點第一個商品 ──
            self.after(0, lambda: self._status_var.set("步驟 3/3：等待結果，點擊第一項商品..."))
            first_item = wait.until(
                EC.element_to_be_clickable((
                    By.CSS_SELECTOR,
                    "div.waterfall-item a"
                ))
            )
            first_item.click()
            self.after(0, lambda: self._status_var.set(f"✅ 已開啟「{name}」商品頁，請直接下單！"))

        except Exception as e:
        
            fallback = f"https://shop.pxgo.com.tw/hourArrive/search/result?q={quote(name)}"
            driver.get(fallback)
            self.after(0, lambda: self._status_var.set(
                f"⚠️ 自動點擊失敗，已跳至搜尋結果頁（{e}）"))


if __name__ == "__main__":
    app = PxmartApp()
    app.mainloop()
