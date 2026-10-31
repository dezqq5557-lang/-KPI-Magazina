from flask import Flask, request, redirect, url_for, render_template_string, flash, Response, send_from_directory
import sqlite3, csv, io, os
from datetime import datetime

DB="shop.db"
app=Flask(__name__)
app.secret_key=os.environ.get("KPI_SECRET","change-me")

SCHEMA="""
CREATE TABLE IF NOT EXISTS sales(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 date TEXT NOT NULL, time TEXT, amount REAL NOT NULL,
 employee TEXT, category TEXT, product TEXT,
 quantity REAL DEFAULT 1, cost REAL DEFAULT 0, type TEXT DEFAULT 'sale',
 external_id TEXT UNIQUE
);
CREATE TABLE IF NOT EXISTS employees(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT);
"""

def db():
    c=sqlite3.connect(DB)
    c.row_factory=sqlite3.Row
    return c
def init():
    c=db(); c.executescript(SCHEMA); c.commit(); c.close()
def setting(k,default=""):
    c=db(); r=c.execute("SELECT value FROM settings WHERE key=?",(k,)).fetchone(); c.close()
    return r["value"] if r else default
def money(x): return f"{x:,.2f} ₽".replace(",", " ").replace(".", ",")
def metrics(date=None):
    c=db()
    where="WHERE date=?" if date else ""
    args=(date,) if date else ()
    rows=c.execute(f"SELECT * FROM sales {where} ORDER BY date DESC,time DESC",args).fetchall()
    sales=[r for r in rows if r["type"]!="refund"]
    refunds=[r for r in rows if r["type"]=="refund"]
    revenue=sum(r["amount"] for r in sales)-sum(abs(r["amount"]) for r in refunds)
    checks=len(sales); avg=revenue/checks if checks else 0
    profit=sum((r["amount"]-r["cost"]*r["quantity"]) for r in sales)-sum(abs(r["amount"]) for r in refunds)
    plan=float(setting("daily_plan","3000") or 0)
    return revenue,checks,avg,profit,plan,rows

HTML=r"""
<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#101b33"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.json"><link rel="apple-touch-icon" href="/static/icon-192.png"><title>KPI Магазина</title>
<style>
:root{--navy:#101b33;--blue:#4263eb;--bg:#f4f6fb;--text:#182238;--muted:#7b8498;--line:#e8ecf4;--green:#16a36a;--shadow:0 8px 28px rgba(25,42,80,.06)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;-webkit-text-size-adjust:100%}
.wrap{max-width:1380px;margin:auto;padding:26px 30px 48px}.top{display:flex;align-items:center;justify-content:space-between;gap:20px;margin-bottom:30px}.brand{display:flex;align-items:center;gap:12px;font-size:17px;font-weight:800;letter-spacing:.2px}.logo{width:42px;height:42px;border-radius:14px;background:linear-gradient(135deg,#5275ff,#263fbd);display:grid;place-items:center;color:#fff;font-weight:900;font-size:20px;box-shadow:0 7px 18px #4263eb44}.nav{display:flex;align-items:center;gap:7px;background:#fff;border:1px solid var(--line);padding:6px;border-radius:14px;box-shadow:var(--shadow)}.nav a{color:#69748b;text-decoration:none;padding:10px 15px;border-radius:10px;font-weight:650}.nav a.active,.nav a:hover{background:#edf1ff;color:#3154d8}
h1{font-size:clamp(25px,3vw,34px);letter-spacing:-.8px;margin:0 0 7px}.subtitle{color:var(--muted);margin:0}.heading{display:flex;justify-content:space-between;align-items:end;gap:16px;margin:8px 0 24px}.date-pill{background:#fff;border:1px solid var(--line);padding:10px 14px;border-radius:11px;color:#66718a;font-weight:600}.cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:15px;margin:22px 0}.card{background:#fff;border:1px solid var(--line);border-radius:17px;padding:20px;min-width:0;box-shadow:var(--shadow)}.metric{position:relative;overflow:hidden}.metric:after{content:"";position:absolute;width:86px;height:86px;border-radius:50%;right:-28px;top:-32px;background:#eef2ff}.metric-label{color:var(--muted);font-size:13px;font-weight:650;position:relative;z-index:1}.v{font-size:clamp(21px,2.2vw,29px);font-weight:800;letter-spacing:-.7px;margin-top:12px;overflow-wrap:anywhere;position:relative;z-index:1}.metric small{display:block;color:#9aa3b5;margin-top:8px;font-size:12px}.panel-grid{display:grid;grid-template-columns:1.25fr 1fr;gap:16px;margin-top:16px}.panel-title{font-size:16px;font-weight:750;margin:0 0 5px}.panel-sub{font-size:12px;color:var(--muted);margin-bottom:18px}.bar{display:flex;align-items:end;height:190px;gap:8px;padding:8px 2px 24px;border-bottom:1px solid var(--line);overflow:hidden}.bar i{flex:1;min-width:8px;background:linear-gradient(180deg,#7892ff,#4263eb);border-radius:7px 7px 3px 3px;min-height:3px;position:relative;transition:opacity .2s}.bar i:hover{opacity:.72}.bar span{position:absolute;bottom:-22px;left:50%;transform:translateX(-50%);font-size:10px;color:#9aa3b5;font-style:normal}.table-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:10px}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{padding:13px 11px;border-bottom:1px solid #eff1f6;text-align:left}th{color:#8a93a6;font-size:11px;text-transform:uppercase;letter-spacing:.5px}td{font-size:13px}tbody tr:last-child td{border-bottom:0}.flash{padding:13px 15px;background:#e9f8f1;color:#087b4c;border-radius:11px;margin:14px 0}.form-card{max-width:680px}.field-label{display:block;font-size:13px;font-weight:700;color:#58647a;margin:0 0 8px}input{padding:13px 14px;border:1px solid #dce2ed;border-radius:10px;font:inherit;max-width:100%;min-height:46px;background:#fff;color:var(--text)}input:focus{outline:3px solid #4263eb22;border-color:#7892ff}input[type=file]{width:100%}form{max-width:100%}.btn{background:linear-gradient(135deg,#5275ff,#3154d8);color:white;border:0;padding:13px 19px;border-radius:10px;cursor:pointer;font-size:14px;font-weight:700;min-height:46px;box-shadow:0 5px 14px #4263eb33}.btn:hover{filter:brightness(1.04)}.muted{color:var(--muted)}.empty{padding:18px;color:#9aa3b5;text-align:center}.footer{color:#a0a8b8;font-size:11px;text-align:center;margin-top:28px}
@media(max-width:1000px){.cards{grid-template-columns:repeat(3,minmax(0,1fr))}.panel-grid{grid-template-columns:1fr}}
@media(max-width:620px){.wrap{padding:15px 13px 32px}.top{display:block;margin-bottom:23px}.brand{margin:2px 2px 15px}.nav{width:100%;justify-content:space-between;gap:2px}.nav a{padding:10px 9px;font-size:13px;text-align:center;flex:1}.heading{align-items:start;display:block;margin-bottom:17px}.date-pill{display:inline-block;margin-top:12px}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:15px 0}.card{padding:15px;border-radius:14px}.v{font-size:21px;margin-top:10px}.metric-label{font-size:12px}.metric small{font-size:10px}.panel-grid{gap:10px;margin-top:10px}.bar{height:165px;gap:5px}.btn{width:100%}input:not([type=file]){width:100%}th,td{padding:11px 9px}.footer{margin-top:20px}}
</style></head><body><div class="wrap">
<header class="top"><div class="brand"><div class="logo">K</div><span>KPI <span style="color:#4263eb">МАГАЗИНА</span></span></div><nav class="nav"><a href="/" class="{{ 'active' if active=='home' else '' }}">Обзор</a><a href="/import" class="{{ 'active' if active=='import' else '' }}">Импорт данных</a><a href="/settings" class="{{ 'active' if active=='settings' else '' }}">Настройки</a></nav></header>
{{body|safe}}<div class="footer">KPI Магазина · Панель аналитики</div></div><script>if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}));}</script></body></html>
"""

def page(content, active="home"): return render_template_string(HTML,body=content,active=active)

@app.route("/")
def home():
    d=request.args.get("date") or datetime.now().strftime("%Y-%m-%d")
    rev,ch,avg,profit,plan,rows=metrics(d)
    pct=(rev/plan*100 if plan else 0)
    hours=[0]*24
    emp={}
    for r in rows:
        if r["type"]=="refund": continue
        try: hours[int((r["time"] or "00:00").split(":")[0])]+=r["amount"]
        except: pass
        emp[r["employee"] or "Без сотрудника"]=emp.get(r["employee"] or "Без сотрудника",0)+r["amount"]
    mx=max(hours) or 1
    bars="".join(f'<i style="height:{max(2,v/mx*190):.0f}px"><span>{h}</span></i>' for h,v in enumerate(hours) if 9<=h<=22)
    ranking="".join(f"<tr><td>{n}</td><td>{money(v)}</td></tr>" for n,v in sorted(emp.items(),key=lambda x:-x[1]))
    body=f"""<div class=heading><div><h1>Обзор магазина</h1><p class=subtitle>Ключевые показатели и динамика продаж</p></div><div class=date-pill>▣ &nbsp;{d}</div></div>
    <div class=cards>
    <div class="card metric"><div class=metric-label>ВЫРУЧКА</div><div class=v>{money(rev)}</div></div>
    <div class="card metric"><div class=metric-label>ЧЕКИ</div><div class=v>{ch}</div></div>
    <div class="card metric"><div class=metric-label>СРЕДНИЙ ЧЕК</div><div class=v>{money(avg)}</div></div>
    <div class="card metric"><div class=metric-label>ПРИБЫЛЬ</div><div class=v>{money(profit)}</div></div>
    <div class="card metric"><div class=metric-label>ВЫПОЛНЕНИЕ ПЛАНА</div><div class=v>{pct:.1f}%</div></div></div>
    <div class=panel-grid><div class=card><h3 class=panel-title>Продажи по часам</h3><div class=panel-sub>Распределение выручки в течение дня</div><div class=bar>{bars}</div></div>
    <div class=card><h3 class=panel-title>Рейтинг сотрудников</h3><div class=panel-sub>Сравнение по выручке за день</div><div class=table-wrap><table><tr><th>Сотрудник</th><th>Выручка</th></tr>{ranking or '<tr><td colspan=2>Нет данных</td></tr>'}</table></div></div></div>
    <br><div class=card><h3 class=panel-title>Последние чеки</h3><div class=panel-sub>Последние 30 операций</div><div class=table-wrap><table><tr><th>Дата</th><th>Время</th><th>Сумма</th><th>Сотрудник</th><th>Категория</th><th>Тип</th></tr>
    {''.join(f"<tr><td>{r['date']}</td><td>{r['time']}</td><td>{money(r['amount'])}</td><td>{r['employee'] or ''}</td><td>{r['category'] or ''}</td><td>{r['type']}</td></tr>" for r in rows[:30]) or '<tr><td colspan=6>Нет данных</td></tr>'}</table></div></div>"""
    return page(body, "home")

@app.route("/import",methods=["GET","POST"])
def imp():
    if request.method=="POST":
        f=request.files.get("file")
        if not f: return page("<h1>Импорт</h1><p>Файл не выбран.</p>")
        text=f.read().decode("utf-8-sig")
        c=db(); n=0
        for row in csv.DictReader(io.StringIO(text)):
            ext=row.get("external_id") or f"{row.get('date')}|{row.get('time')}|{row.get('amount')}|{row.get('employee')}|{n}"
            try:
                c.execute("""INSERT OR IGNORE INTO sales(date,time,amount,employee,category,product,quantity,cost,type,external_id)
                VALUES(?,?,?,?,?,?,?,?,?,?)""",(row.get("date"),row.get("time",""),float(row.get("amount",0)),row.get("employee",""),row.get("category",""),row.get("product",""),float(row.get("quantity",1) or 1),float(row.get("cost",0) or 0),row.get("type","sale"),ext))
                n+=1
            except Exception: pass
        c.commit(); c.close()
        flash(f"Обработано строк: {n}")
        return redirect(url_for("imp"))
    body="""<div class=heading><div><h1>Импорт данных</h1><p class=subtitle>Загрузка отчётов о продажах из CSV</p></div></div><p class=muted>Первый рабочий канал — CSV. Позже сюда подключается автоматический API-клиент Контур.ОФД.</p>
    <form method=post enctype=multipart/form-data class="card form-card"><label class=field-label>Выберите CSV-файл</label><input type=file name=file accept=.csv required><br><br><button class=btn>Загрузить данные</button></form>
    <br><div class=card><b>Колонки:</b> date,time,amount,employee,category,product,quantity,cost,type,external_id</div>"""
    return page(body, "import")

@app.route("/settings",methods=["GET","POST"])
def settings():
    if request.method=="POST":
        c=db(); c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('daily_plan',?)",(request.form.get("plan","3000"),)); c.commit(); c.close()
        return redirect(url_for("settings"))
    body=f"""<div class=heading><div><h1>Настройки</h1><p class=subtitle>Параметры и интеграции магазина</p></div></div><div class="card form-card"><form method=post>
    <label class=field-label>План продаж на день, ₽</label><input name=plan type=number min=0 step=0.01 value="{setting('daily_plan','3000')}"><br><br>
    <button class=btn>Сохранить настройки</button></form></div>
    <br><div class=card form-card><h3 class=panel-title>Контур.ОФД</h3><p class=muted>Модуль интеграции будет подключён после получения официального API-доступа. Секреты не хранятся в HTML и не публикуются.</p></div>"""
    return page(body, "settings")

@app.route("/manifest.json")
def manifest():
    return Response('{"name":"KPI Магазина","short_name":"KPI Магазина","start_url":"/","display":"standalone","background_color":"#f4f6f9","theme_color":"#111827","icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]}', mimetype="application/manifest+json")

@app.route("/sw.js")
def service_worker():
    js="""const CACHE='kpi-shell-v1'; self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/','/manifest.json'])))); self.addEventListener('activate',e=>e.waitUntil(self.clients.claim())); self.addEventListener('fetch',e=>{if(e.request.method==='GET' && new URL(e.request.url).origin===location.origin){e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));}});"""
    return Response(js, mimetype="application/javascript", headers={"Service-Worker-Allowed":"/"})

if __name__=="__main__":
    init(); app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8000)),debug=False)
