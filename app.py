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
<meta name="theme-color" content="#111827"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.json"><link rel="apple-touch-icon" href="/static/icon-192.png">
<title>KPI Магазина</title><style>
*{box-sizing:border-box}body{margin:0;font:15px Arial,sans-serif;background:#f4f6f9;color:#172033;-webkit-text-size-adjust:100%}.wrap{max-width:1250px;margin:auto;padding:22px}
nav{background:#111827;color:white;padding:15px 18px;border-radius:12px;margin-bottom:20px;display:flex;align-items:center;gap:18px;flex-wrap:wrap}nav b{margin-right:8px}nav a{color:white;text-decoration:none;padding:7px 0}nav a:hover{text-decoration:underline}
h1{margin:0 0 8px;font-size:clamp(23px,4vw,32px)}h3{margin:0 0 14px}.muted{color:#687386}.cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px;margin:20px 0}
.card{background:white;border:1px solid #e4e7ec;border-radius:12px;padding:17px;min-width:0}.v{font-size:clamp(20px,2.4vw,26px);font-weight:700;margin-top:8px;overflow-wrap:anywhere}
table{width:100%;border-collapse:collapse;background:white;white-space:nowrap}th,td{padding:11px 10px;border-bottom:1px solid #e8ebef;text-align:left}th{color:#687386;font-size:13px}.btn{background:#2563eb;color:white;border:0;padding:12px 17px;border-radius:9px;cursor:pointer;font-size:15px;min-height:44px}input{padding:12px;border:1px solid #d8dde6;border-radius:8px;font:inherit;max-width:100%;min-height:44px}input[type=file]{width:100%}form{max-width:100%}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.bar{display:flex;align-items:end;height:220px;gap:6px;overflow:hidden}.bar i{flex:1;background:#60a5fa;border-radius:5px 5px 0 0;min-height:2px;position:relative}.bar span{position:absolute;bottom:-20px;font-size:10px}.table-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:8px}.table-wrap table{min-width:560px}.flash{padding:12px;background:#ecfdf5;border-radius:8px;margin:12px 0}
@media(max-width:900px){.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}}
@media(max-width:600px){.wrap{padding:12px}.cards{gap:8px;margin:14px 0}.card{padding:13px;border-radius:10px}.v{font-size:21px}nav{margin:0 0 15px;padding:13px;border-radius:10px;gap:12px}nav b{width:100%;margin:0}nav a{padding:5px 0;font-size:14px}.bar{height:180px}.btn{width:100%}input:not([type=file]){width:100%}th,td{padding:10px 8px}}
</style></head><body><div class="wrap">
<nav><b>KPI МАГАЗИНА</b><a href="/">Главная</a><a href="/import">Импорт</a><a href="/settings">Настройки</a></nav>
{{body|safe}}</div><script>if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}));}</script></body></html>
"""

def page(content): return render_template_string(HTML,body=content)

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
    body=f"""<h1>Показатели магазина</h1><div class=muted>{d}</div>
    <div class=cards>
    <div class=card>Выручка<div class=v>{money(rev)}</div></div>
    <div class=card>Чеки<div class=v>{ch}</div></div>
    <div class=card>Средний чек<div class=v>{money(avg)}</div></div>
    <div class=card>Прибыль<div class=v>{money(profit)}</div></div>
    <div class=card>План<div class=v>{pct:.1f}%</div></div></div>
    <div class=grid><div class=card><h3>Продажи по часам</h3><div class=bar>{bars}</div></div>
    <div class=card><h3>Рейтинг сотрудников</h3><div class=table-wrap><table><tr><th>Сотрудник</th><th>Выручка</th></tr>{ranking or '<tr><td colspan=2>Нет данных</td></tr>'}</table></div></div></div>
    <br><div class=card><h3>Последние чеки</h3><div class=table-wrap><table><tr><th>Дата</th><th>Время</th><th>Сумма</th><th>Сотрудник</th><th>Категория</th><th>Тип</th></tr>
    {''.join(f"<tr><td>{r['date']}</td><td>{r['time']}</td><td>{money(r['amount'])}</td><td>{r['employee'] or ''}</td><td>{r['category'] or ''}</td><td>{r['type']}</td></tr>" for r in rows[:30]) or '<tr><td colspan=6>Нет данных</td></tr>'}</table></div></div>"""
    return page(body)

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
    body="""<h1>Импорт данных</h1><p class=muted>Первый рабочий канал — CSV. Позже сюда подключается автоматический API-клиент Контур.ОФД.</p>
    <form method=post enctype=multipart/form-data class=card><input type=file name=file accept=.csv required> <button class=btn>Загрузить</button></form>
    <br><div class=card><b>Колонки:</b> date,time,amount,employee,category,product,quantity,cost,type,external_id</div>"""
    return page(body)

@app.route("/settings",methods=["GET","POST"])
def settings():
    if request.method=="POST":
        c=db(); c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('daily_plan',?)",(request.form.get("plan","3000"),)); c.commit(); c.close()
        return redirect(url_for("settings"))
    body=f"""<h1>Настройки</h1><div class=card><form method=post>
    <label>План на день, ₽</label><br><input name=plan value="{setting('daily_plan','3000')}"><br><br>
    <button class=btn>Сохранить</button></form></div>
    <br><div class=card><h3>Контур.ОФД</h3><p class=muted>Модуль интеграции будет подключён после получения официального API-доступа. Секреты не хранятся в HTML и не публикуются.</p></div>"""
    return page(body)

@app.route("/manifest.json")
def manifest():
    return Response('{"name":"KPI Магазина","short_name":"KPI Магазина","start_url":"/","display":"standalone","background_color":"#f4f6f9","theme_color":"#111827","icons":[{"src":"/static/icon-192.png","sizes":"192x192","type":"image/png"},{"src":"/static/icon-512.png","sizes":"512x512","type":"image/png"}]}', mimetype="application/manifest+json")

@app.route("/sw.js")
def service_worker():
    js="""const CACHE='kpi-shell-v1'; self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(['/','/manifest.json'])))); self.addEventListener('activate',e=>e.waitUntil(self.clients.claim())); self.addEventListener('fetch',e=>{if(e.request.method==='GET' && new URL(e.request.url).origin===location.origin){e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));}});"""
    return Response(js, mimetype="application/javascript", headers={"Service-Worker-Allowed":"/"})

if __name__=="__main__":
    init(); app.run(host="0.0.0.0",port=int(os.environ.get("PORT",8000)),debug=False)
