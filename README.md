
# ESPUPS

> [!IMPORTANT]
> 這是一個尚未完成的作品

## 專案概述

這是一個以 **ESP32-P4** 為核心的電池備援系統，具備雙繼電器電源切換邏輯、即時電壓監控，以及透過後端進行雲端控制。系統會追蹤電池狀況、管理電源模式，並透過 Discord 發送狀態更新通知。 

---

## 零件清單 (Item List!!)

> [!NOTE]
> 買零件時記得多買 1 到 2 個備用喔！ 
> 因為 ~~焊的時候總會壞幾個~~

| 零件 | 規格/數據 | 數量 | 價格 (估計) |
|----|----|------|--------|
| 二極體 | 1N5822 3A/40V (肖特基) | 3 | 每顆約 0.86 NTD |
| 電容器 | 16x25 25V/4700UF 電解電容 | 3 | 每顆約 19 NTD |
| ESP32 | 一般 / S3 / P4 皆可 | 1 | 約 75~100 NTD (挑便宜的買就對了) |
| Type-C 接口 | 輸入/輸出 | 5(相信我) | 每個 2.35NTD |
| Type-C線 | 3A 50CM | 1 | 一條 8 NTD |
| 升壓+充電板 | 建議輸出至少20W 輸入25W | 1 | 一塊 200~300 NTD |
| 鋰電池 | 10000mah | 4 | 一顆 99 NTD |
| 電阻 | 200k | 4 | 一條 0.3 NTD |

### 引腳資料(需依照自己使用的開發板選擇。)
- **電壓監控腳位 (GPIO 20)**：透過 ADC 監控電池電壓。
- **充電偵測腳位 (GPIO 21)**：偵測 USB/充電狀態。
- **繼電器控制腳位**：GPIO 2 (R1), GPIO 27 (R2)

### 繼電器配置

```text
R1 (GPIO 2)
├─ NC  → R2 的 NC
├─ COM → 變壓器
└─ NO  → R2 的 NO

R2 (GPIO 27)
├─ NC  → R1 的 NC
├─ COM → 輸出端電容
└─ NO  → UPS 電池端 + R1 的 NO
```

**電源模式映射表：**
| R1 狀態 | R2 狀態 | 模式 | 輸出來源 |
|----|----|------|--------|
| ON | ON | 無輸出 | 無 (關機) |
| ON | OFF | 純電池 | 僅電池供電 |
| OFF | OFF | 混合模式 | 電池 + 變壓器混合 |
| OFF | ON | 純變壓器 | 僅變壓器供電 |

---

## 軟體架構

### 後端伺服器 (FastAPI)

**API 端點：`/UpdateData` (POST)**
- 。
- 以 JSONL 格式儲存 (`UPSdata.jsonl`)。
- 參數：`secToken`, `v` (電壓), `p` (百分比), `chg` (充電狀態), `r1`, `r2`(繼電器莊太)。
- 回傳：成功 200，驗證失敗 401，格式錯誤 400。

**API 端點：`/GetData` (GET/POST)**
- 回傳所有儲存的紀錄 (GET)。
- 支援過濾功能(要用POST)：
  - `range`：回傳最後 N 筆紀錄。
  - `TSFROM`/`TSTO`：透過時間戳記範圍過濾。
  - 回傳格式為 Json inside array (jsonl)

**API 端點：`/SetRelay` (POST)**
- 遠端設定繼電器狀態。
- **需要密碼**
- 輸入參數：`r1` (0/1), `r2` (0/1), `secToken`。
- 將指令存入 `pending_command` 隊列中。

**API 端點：`/GetCommand` (GET)**
- ESP32 每 2 秒抓取一次。
- 回傳待處理的繼電器指令（若有）。
- 讀取後自動清除。

### 數據格式 (Data Format)

JSONL 格式如下：
```json
{
  "v": 12.34,
  "p": 85,
  "chg": true,
  "r1": 0,
  "r2": 1,
  "possibleMode": "WALL ONLY",
  "ts": 1710000000 //Timestamp 由伺服器處理
}
```

---

## 關於 ESP32-P4....
### 資料更新
- **每 200ms**：發送數據更新至 FastAPI 伺服器。 
- **每 60 秒**：透過 Vercel 代理發送 Discord 通知。
- **每 2 秒**：輪詢 `/GetCommand` 以獲取遠端控制指令。
- 支援透過Serial Console 手動輸入指令。

### Serial Console 指令
```text
send       → 發送測試通知到 Discord (經過Vercel中轉。)
ssend      → 發送數據到 FastAPI 伺服器
r1 / r2    → 改變繼電器(開改關、關改開)
pwrwall    → 設定為純變壓器模式 (R1=1, R2=1)
pwrb+w     → 設定為混合模式 (R1=0, R2=0)
pwrbat     → 設定為純電池模式 (R1=1, R2=0)
pwrno      → 設定為無輸出 (R1=0, R2=1)
help       → 顯示指令說明
```

---

## 對使用者

### Discord 通知系統

**Vercel 代理路徑：** `https://dcproxy.chiuhuang.dev/ups-ping`
- 需要 `x-vercel-protection-bypass` Header。
- 發送包含以下內容的嵌入式訊息 (Embeds)：電壓、電池百分比、充電狀態、繼電器狀態。
 ![Example Discord NotifyPreview](image.png)

  [Github REPO](https://github.com/ChiuHuang/Discord-Webhook-Proxy/blob/main/api/index.py)
> [!NOTE]
> 你可以直接用Webhook，我是因為當初C6軟體太舊才除錯到那裡。
---

## Frontend：Flet
![Flet Preview](image-1.png)
- 即時電壓圖表
- 電池百分比與充電狀態
- 目前電源模式
- 電源模式控制

> [!NOTE]
> 建議前端不要編譯，用伺服器跑可以避免Endpoint外流，還可以降低Backend的壓力。
---

## API 身分驗證

所有涉及修改數據的端點皆需驗證：
```text
secToken: "TangTangIsCute.53098756789"
```
*just look at her*

---

## (之後修......)
> Flet Dashboard加時間選擇 (7h/24h/7d/30d)

