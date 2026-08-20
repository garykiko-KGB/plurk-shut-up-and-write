# plurk-shut-up-and-write

A Plurk-based online writing session service inspired by Shut Up & Write! 

一個基於 Plurk 的線上寫作活動服務，靈感來自 Shut Up & Write!


----

# Shut Up and Write!

受到 Shut Up & Write! 啟發的 Plurk Bot。

這個 Bot 的目的，是讓人們可以在 Plurk 上一起進行一段專注時間。每個人可以做自己的事情，不需要討論，也不需要互相認識；只要知道此刻有人和自己一起專心做事，就足夠了。

雖然最初是以「寫作」為主要用途，但任何需要一段專注時間、時間管理或持續培養的活動，都可以使用這個 Bot。

## 核心理念

Bot 不管理人，Bot 管理時間。

Bot 不要求使用者報到，也不追蹤誰有沒有參加、什麼時候加入或什麼時候離開。

它只負責：

告訴大家什麼時候開始
告訴大家什麼時候休息
告訴大家下一回合什麼時候開始
在活動結束後提供一個可以分享成果、感想與過程的空間

想加入的人可以一起進行；想安靜做事的人也可以完全不發言。

## 運作方式

使用者可以在 Plurk 上呼叫 Bot，建立一場活動，設定：

每回合的執行時間
休息時間
回合數
開始前的準備時間

Bot 會建立一則獨立的活動 Plurk，並在原本的呼叫訊息下回覆活動連結。

活動開始前，可以自由分享今天的目標。

活動開始後，Bot 進行計時，並在每回合結束時提醒休息與下一回合的開始時間。

活動結束後，參與者可以自由分享今天完成了什麼、遇到了什麼、或只是單純聊聊這段過程。

分享不是強制的。

## 番茄工作法

活動時間設定以 Pomodoro Technique（番茄工作法） 作為參考。

一般建議：

專注時間：15～25 分鐘
休息時間：5～10 分鐘
一組約 4～8 回合
完成一組後進行較長的休息

實際時間可以依個人需求調整。

## 目前狀態

🚧 開發中

## 目錄圖

```text
plurk-shut-up-and-write/
│
├── core/
│   ├── __init__.py
│   ├── activity.py
│   ├── activity_manager.py
│   ├── activity_scheduler.py
│   └── activity_service.py
│
├── handlers/
│   ├── __init__.py
│   └── response_handler.py
│
├── parsers/
│   ├── __init__.py
│   └── command_parser.py
│
├── services/
│   ├── __init__.py
│   ├── plurk_api.py
│   ├── plurk_realtime.py
│   └── plurk_publisher.py
│
├── tests/
│   ├── __init__.py
│   ├── test_activity.py
│   ├── test_activity_manager.py
│   ├── test_activity_scheduler.py
│   ├── test_activity_service.py
│   ├── test_command_parser.py
│   ├── test_plurk_realtime.py
│   └── test_response_handler.py
│
├── tools/
│   └── realtime_test.py
│
├── README.md
├── idea.md
├── requirements.txt
├── LICENSE
└── .gitignore
```
