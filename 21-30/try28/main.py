import re as ree
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, Query, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(debug=True)
app.add_middleware(SessionMiddleware, secret_key="logic")
app.mount("/static", StaticFiles(directory="static"))

templates = Jinja2Templates(directory="templates")

def get_db():
    conn = psycopg2.connect(
        dbname = "korochki",
        user = "postgres",
        password = "qwerty",
        host = "localhost",
        port = "5432"
    )
    conn.cursor_factory = psycopg2.extras.DictCursor
    return conn

def init_db():
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("""
create table if not exists users(
                    id serial primary key,
                    login text unique not null,
                    password text not null,
                    fio text not null,
                    phone text not null,
                    email text not null);
                    """)
        cur.execute("""
create table if not exists requests(
                    id serial primary key,
                    user_id integer references users(id) on delete cascade,
                    course_name text not null,
                    date_start text not null,
                    payment_method text not null,
                    status text default "Новая",
                    review text);
                    """)
        conn.commit()
    
init_db()

@app.get("/")
def get_base(request: Request):
    return RedirectResponse(url="/login", status_code=302)

@app.get("/logout")
def get_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

@app.get("/register")
def get_register(request: Request):
    return templates.TemplateResponse(request=request, name="register.html", context={"error": None})

@app.post("/register")
def post_register(request: Request,
                  login: str = Form(...),
                  password: str = Form(...),
                  fio: str = Form(...),
                  phone: str = Form(...),
                  email: str = Form(...)):
    error = None

    if not ree.fullmatch(r'[a-zA-Z0-9]{6,}', login):
        error = "Логин: Латиница и цифры, 6 символов минимум"
    elif len(password) < 8:
        error = "Пароль: 8 символов минимум"
    elif not ree.fullmatch(r'[а-яА-ЯёЁ\s]+', fio):
        error = "ФИО: Кириллица и пробелы"
    elif not ree.fullmatch(r'8\(\d{3}\)\d{3}-\d{2}-\d{2}', phone):
        error = "Телефон: Формата 8(XXX)XXX-XX-XX"
    elif not ree.fullmatch(r'[^@]+@[^@]+\.[^@]+', email):
        error = "Почта: Неверный формат"
    else:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("select * from users where login = %s", (login,))
            user = cur.fetchone()

            if not user:
                cur.execute("insert into users (login, password, fio, phone, email) values (%s, %s, %s, %s, %s)", (login, password, fio, phone, email))
                conn.commit()
                return RedirectResponse(url="/login", status_code=302)
            else:
                error = "Логин уже занят"
    return templates.TemplateResponse(request=request, name="register.html", context={"error": error, "login": login, "password": password, "fio": fio, "phone": phone, "email": email})

@app.get("/login")
def get_login(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@app.post("/login")
def post_login(request: Request,
               login: str = Form(...),
               password: str = Form(...)):
    if login == "Admin":
        if password == "KorokNET":
            request.session["admin"] = True
            return RedirectResponse(url="/admin", status_code=302)
        else:
            return templates.TemplateResponse(request=request, name="login.html", context={"error": "Неверные данные"})
        
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("select * from users where login = %s", (login,))
        user = cur.fetchone()

        if user and user["password"] == password:
            request.session["user_id"] = user["id"]
            return RedirectResponse(url="/profile", status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": "Неверные данные"})

@app.get("/profile")
def get_profile(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("select * from requests where user_id = %s", (user_id,))
        request_list = cur.fetchall()
    return templates.TemplateResponse(request=request, name="profile.html", context={"requests": request_list})

@app.post("/add_review")
def post_add_review(request: Request,
                    review: str = Form(...),
                    request_id: str = Form(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)    
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("update set review = %s where id = %s", (review, request_id))
        conn.commit()
    return RedirectResponse(url="/profile", status_code=302)

COURSES = [
    "Основы алгоритмизации и программирования",
    "Основы веб-дизайна",
    "Основы проектирования баз данных",
]
PAYMENTS = ["наличными", "переводом по номеру телефона"]

@app.get("/create_request")
def get_create_request(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)      
    return templates.TemplateResponse(request=request, name="create_request.html", context={"courses": COURSES, "payments": PAYMENTS})

@app.post("/create_request")
def post_create_request(request: Request,
                        course: str = Form(...),
                        date: str = Form(...),
                        payment: str = Form(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)     

    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("insert into requests (course_name, date_start, payment_method, user_id) values (%s, %s, %s, %s)", (course, date, payment, user_id))
        conn.commit()
    return RedirectResponse(url="/profile", status_code=302)     

@app.get("/admin")
def get_admin(request: Request, 
              status: str | None = Query(None)):
    user_id = request.session.get("admin")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    
    base = "select requests.*, users.login, users.fio from requests, users where user_id = requests.user_id"
    params = []

    if status and status != "Все":
        base += " and status = %s"
        params.append(status)
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute(base, params)
        request_list = cur.fetchall()
    return templates.TemplateResponse(request=request, name="admin.html", context={"requests": request_list, "cur_status": status or "Все"})

@app.post("/admin/change_status")
def post_admin_change_status(request: Request,
                             status: str = Form(...),
                             request_id: str = Form(...)):
    user_id = request.session.get("admin")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    
    with get_db() as conn:
        cur = conn.cursor()
        cur.execute("update requests set status = %s where id = %s", (status, request_id))
        conn.commit()
    return RedirectResponse(url="/admin", status_code=302)