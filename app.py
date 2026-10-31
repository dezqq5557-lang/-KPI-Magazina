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
<meta name="theme-color" content="#0b1224"><meta name="apple-mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<link rel="manifest" href="/manifest.json"><link rel="apple-touch-icon" href="/static/icon-192.png"><title>KPI Магазина</title>
<style>
:root{--ink:#111a2e;--muted:#8490a7;--line:#e9edf5;--paper:#f4f6fb;--navy:#0b1224;--blue:#6478ff;--cyan:#42d6cf;--violet:#9a7bff;--green:#21b987;--orange:#ffb45c;--shadow:0 14px 38px rgba(22,34,65,.07)}
*{box-sizing:border-box}html{background:var(--paper)}body{margin:0;background:radial-gradient(ellipse at 85% -10%,#e5e9ff 0,transparent 35%),var(--paper);color:var(--ink);font:15px Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif;-webkit-text-size-adjust:100%;min-height:100vh}
.wrap{max-width:1460px;margin:auto;padding:26px 34px 50px}.top{display:flex;align-items:center;justify-content:space-between;gap:22px;padding:15px 18px;margin-bottom:34px;background:linear-gradient(115deg,#0b1224,#172747 72%,#23365e);border:1px solid #26395e;border-radius:21px;box-shadow:0 16px 38px #0b122422;color:#fff}.brand{display:flex;align-items:center;gap:13px;font-size:16px;font-weight:850;letter-spacing:.7px}.logo{width:44px;height:44px;border-radius:15px;background:linear-gradient(145deg,#7b8dff,#4b5ee8 55%,#37c8c1);display:grid;place-items:center;color:#fff;font-weight:950;font-size:21px;box-shadow:0 7px 20px #6678ff55}.brand-sub{display:block;font-size:9px;letter-spacing:2.1px;color:#aab8d5;font-weight:700;margin-top:3px}.nav{display:flex;align-items:center;gap:5px;padding:5px;border-radius:13px;background:#ffffff0d;border:1px solid #ffffff17}.nav a{color:#b8c4da;text-decoration:none;padding:11px 16px;border-radius:9px;font-weight:650;font-size:13px;transition:.2s}.nav a.active,.nav a:hover{background:linear-gradient(120deg,#6579ff,#5366e7);color:#fff;box-shadow:0 5px 15px #5366e744}
h1{font-size:clamp(26px,3vw,36px);letter-spacing:-1.1px;margin:0 0 8px;font-weight:850}.subtitle{color:#8994aa;margin:0;font-size:14px}.heading{display:flex;justify-content:space-between;align-items:end;gap:16px;margin:5px 0 25px}.date-pill{background:#fff;border:1px solid #e6eaf3;padding:11px 15px;border-radius:12px;color:#66728b;font-weight:700;font-size:13px;box-shadow:0 5px 18px #18274708}.cards{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:15px;margin:22px 0}.card{background:#fff;border:1px solid #e9edf5;border-radius:19px;padding:21px;min-width:0;box-shadow:var(--shadow)}.metric{position:relative;overflow:hidden;min-height:145px;isolation:isolate}.metric:before{content:"";position:absolute;width:115px;height:115px;border-radius:50%;right:-38px;top:-45px;background:var(--tint,#edf0ff);z-index:-1}.metric:after{content:"";position:absolute;width:70px;height:70px;border-radius:50%;right:20px;bottom:-48px;background:var(--tint,#edf0ff);opacity:.55;z-index:-1}.metric-top{display:flex;align-items:center;justify-content:space-between;gap:8px}.metric-label{color:#7f8aa1;font-size:11px;font-weight:800;letter-spacing:1px}.metric-icon{width:34px;height:34px;display:grid;place-items:center;border-radius:11px;background:var(--tint,#edf0ff);color:var(--accent,#586df1);font-size:16px;font-weight:900}.v{font-size:clamp(21px,2vw,29px);font-weight:850;letter-spacing:-.8px;margin-top:15px;overflow-wrap:anywhere;color:#17223a}.metric small{display:block;color:#9ba5b7;margin-top:7px;font-size:11px}.metric.revenue{--accent:#6578f5;--tint:#edf0ff}.metric.checks{--accent:#1ba98d;--tint:#e5f8f3}.metric.average{--accent:#a078ed;--tint:#f2ecff}.metric.profit{--accent:#e59a43;--tint:#fff3e4}.metric.plan{--accent:#299cc0;--tint:#e5f6fb}
.panel-grid{display:grid;grid-template-columns:1.25fr 1fr;gap:17px;margin-top:17px}.panel-title{font-size:16px;font-weight:800;margin:0 0 6px;letter-spacing:-.2px}.panel-sub{font-size:12px;color:#9aa4b6;margin-bottom:19px}.bar{display:flex;align-items:end;height:190px;gap:9px;padding:8px 2px 25px;border-bottom:1px solid var(--line);overflow:hidden}.bar i{flex:1;min-width:8px;background:linear-gradient(180deg,#53d4d0 0%,#6679ff 85%);border-radius:8px 8px 3px 3px;min-height:3px;position:relative;box-shadow:0 4px 12px #6478ff1c;transition:filter .2s}.bar i:hover{filter:brightness(1.12)}.bar span{position:absolute;bottom:-22px;left:50%;transform:translateX(-50%);font-size:10px;color:#9aa4b6;font-style:normal}.table-wrap{width:100%;overflow-x:auto;-webkit-overflow-scrolling:touch;border-radius:11px}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{padding:13px 11px;border-bottom:1px solid #eff2f7;text-align:left}th{color:#9aa4b6;font-size:10px;text-transform:uppercase;letter-spacing:.8px}td{font-size:13px;color:#4d5a72}tbody tr:last-child td{border-bottom:0}tbody tr:hover{background:#f8f9fd}.flash{padding:13px 15px;background:#e8f8f2;color:#087b4c;border-radius:11px;margin:14px 0}.form-card{max-width:720px}.field-label{display:block;font-size:13px;font-weight:750;color:#58647a;margin:0 0 9px}input{padding:13px 14px;border:1px solid #dce2ed;border-radius:11px;font:inherit;max-width:100%;min-height:47px;background:#fff;color:var(--ink)}input:focus{outline:3px solid #6478ff22;border-color:#8493ff}input[type=file]{width:100%}form{max-width:100%}.btn{background:linear-gradient(120deg,#687cff,#4d60e6);color:white;border:0;padding:13px 20px;border-radius:11px;cursor:pointer;font-size:14px;font-weight:750;min-height:47px;box-shadow:0 7px 18px #566be638;transition:transform .15s,filter .15s}.btn:hover{filter:brightness(1.06);transform:translateY(-1px)}.muted{color:var(--muted)}.empty{padding:18px;color:#9aa3b5;text-align:center}.footer{color:#a3adbf;font-size:11px;text-align:center;margin-top:30px}.progress{height:8px;border-radius:20px;background:#e9edf5;overflow:hidden;margin-top:13px}.progress span{display:block;height:100%;border-radius:20px;background:linear-gradient(90deg,#42cfc4,#6578ff);max-width:100%}.section-card{margin-top:17px}.table-heading{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:14px}.tag{font-size:10px;font-weight:800;letter-spacing:.6px;color:#6478e9;background:#eef0ff;padding:7px 9px;border-radius:8px}
@media(max-width:1050px){.cards{grid-template-columns:repeat(3,minmax(0,1fr))}.panel-grid{grid-template-columns:1fr}}
@media(max-width:650px){.wrap{padding:12px 11px 28px}.top{display:block;padding:13px;border-radius:17px;margin-bottom:24px}.brand{margin:1px 2px 14px}.logo{width:40px;height:40px}.nav{width:100%;justify-content:space-between;gap:2px}.nav a{padding:10px 7px;font-size:11px;text-align:center;flex:1}.heading{align-items:start;display:block;margin-bottom:16px}.date-pill{display:inline-block;margin-top:12px}.cards{grid-template-columns:repeat(2,minmax(0,1fr));gap:9px;margin:14px 0}.card{padding:15px;border-radius:15px}.metric{min-height:126px}.metric-label{font-size:9px;letter-spacing:.6px}.metric-icon{width:29px;height:29px;border-radius:9px;font-size:14px}.v{font-size:20px;margin-top:12px}.metric small{font-size:10px}.panel-grid{gap:10px;margin-top:10px}.bar{height:160px;gap:5px}.btn{width:100%}input:not([type=file]){width:100%}th,td{padding:11px 9px}.footer{margin-top:22px}}
@media(max-width:360px){.nav a{font-size:10px;padding:9px 4px}.v{font-size:18px}.metric{padding:12px}}
</style></head><body><div class="wrap">
<header class="top"><div class="brand"><div class="logo">K</div><div><span>KPI <span style="color:#9baaff">МАГАЗИНА</span></span><span class="brand-sub">RETAIL ANALYTICS</span></div></div><nav class="nav"><a href="/" class="{{ 'active' if active=='home' else '' }}">Обзор</a><a href="/import" class="{{ 'active' if active=='import' else '' }}">Импорт данных</a><a href="/settings" class="{{ 'active' if active=='settings' else '' }}">Настройки</a></nav></header>
{{body|safe}}<div class="footer">KPI Магазина &nbsp;·&nbsp; Аналитика продаж</div></div><script>if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('/sw.js').catch(()=>{}));}</script></body></html>
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
    body=f"""<div class=heading><div><h1>Обзор магазина</h1><p class=subtitle>Финансовые показатели и эффективность продаж</p></div><div class=date-pill>◷ &nbsp;{d}</div></div>
    <div class=cards>
    <div class="card metric revenue"><div class=metric-top><div class=metric-label>ВЫРУЧКА</div><div class=metric-icon>↗</div></div><div class=v>{money(rev)}</div><small>Продажи за выбранный день</small></div>
    <div class="card metric checks"><div class=metric-top><div class=metric-label>ЧЕКИ</div><div class=metric-icon>▤</div></div><div class=v>{ch}</div><small>Количество покупок</small></div>
    <div class="card metric average"><div class=metric-top><div class=metric-label>СРЕДНИЙ ЧЕК</div><div class=metric-icon>◈</div></div><div class=v>{money(avg)}</div><small>Выручка на один чек</small></div>
    <div class="card metric profit"><div class=metric-top><div class=metric-label>ПРИБЫЛЬ</div><div class=metric-icon>₽</div></div><div class=v>{money(profit)}</div><small>С учётом себестоимости</small></div>
    <div class="card metric plan"><div class=metric-top><div class=metric-label>ВЫПОЛНЕНИЕ ПЛАНА</div><div class=metric-icon>◎</div></div><div class=v>{pct:.1f}%</div><div class=progress><span style="width:{max(0,min(100,pct)):.1f}%"></span></div><small>План: {money(plan)}</small></div></div>
    <div class=panel-grid><div class=card><div class=table-heading><div><h3 class=panel-title>Продажи по часам</h3><div class=panel-sub>Распределение выручки в течение дня</div></div><span class=tag>СЕГОДНЯ</span></div><div class=bar>{bars}</div></div>
    <div class=card><div class=table-heading><div><h3 class=panel-title>Рейтинг сотрудников</h3><div class=panel-sub>По объёму выручки за день</div></div><span class=tag>ТОП</span></div><div class=table-wrap><table><tr><th>Сотрудник</th><th>Выручка</th></tr>{ranking or '<tr><td colspan=2>Нет данных</td></tr>'}</table></div></div></div>
    <div class="card section-card"><div class=table-heading><div><h3 class=panel-title>Последние чеки</h3><div class=panel-sub>Последние 30 операций по магазину</div></div><span class=tag>ОПЕРАЦИИ</span></div><div class=table-wrap><table><tr><th>Дата</th><th>Время</th><th>Сумма</th><th>Сотрудник</th><th>Категория</th><th>Тип</th></tr>
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
