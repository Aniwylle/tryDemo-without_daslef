import sqlite3
from fastapi import Form, FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="Banana") # забыла про бананчик(

templates = Jinja2Templates(directory="templates")

DATABASE = "database.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row #забыла ROW
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript(
            """
create table if not exists users(
                           id integer primary key autoincrement,
                           login text unique not null,
                           password text not null,
                           fio text not null,
                           email text not null,
                           phone text not null
                           );
                           create table if not exists requests(
                           id integer primary key autoincrement,
                           user_id integer references users(id) on delete cascade,
                           course_name text not null,
                           date_start text not null,
                           payment_method text not null,
                           status text not null default "Новая"
                           );
                           """
        ) #подсматривала не все, в основном юзер_айди и как правильно написать крутой autoincrement 

init_db()

@app.get("/")
def get_base(request: Request):
    return RedirectResponse(url="/login", status_code=302)

@app.get("/logout")
def get_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)

@app.get("/login")
def get_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.get("/register")
def get_register(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

@app.post("/register")
def post_register(request: Request,
                  login: str = Form(...),
                  password: str = Form(...),
                  fio: str = Form(...),
                  email: str = Form(...),
                  phone: str = Form(...)):
    with get_db() as conn:
        conn.execute("insert into users (login, password, fio, email, phone) values (?,?,?,?,?)", (login,password,fio,email,phone))
    return RedirectResponse(url="/login", status_code=302)

@app.post("/login")
def post_login(request: Request,
                  login: str = Form(...),
                  password: str = Form(...)):
    if login == "Admin":
        if password == "KorokNET":
            request.session["admin"] = True #подсмотрела
            return RedirectResponse(url="/admin", status_code=302)
        else:
            return templates.TemplateResponse("login.html", {"request": request, "error": "Неверные данные"})
    with get_db() as conn:
        user = conn.execute("select * from users where login = ?", (login,)).fetchone() #забыла запятую в логине
        if user and user["password"] == password: # подсмотрела
            request.session["user_id"] = user["id"] # подсмотрела
            return RedirectResponse(url="/profile", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": "Неверные данные"})

@app.get("/profile")
def get_profile(request: Request):
    user_id = request.session.get("user_id") #почти сама, но пришлось подсмотреть
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    
    with get_db() as conn:
        request_list = conn.execute("select * from requests where user_id = ?", (user_id,)).fetchall() #в скобках изначально написала неправильно, пришлось подсматривать
    return templates.TemplateResponse("profile.html", {"request": request, "requests": request_list})
    
COURSES = ["Киберспорт", "Дизайн", "Роблокс"]
PAYMENTS = ["Наличными", "Перевеод по номеру телефона"]

@app.get("/create_request")
def get_create_request(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse("create_request.html", {"request": request, "courses": COURSES, "payments": PAYMENTS})

@app.post("/create_request")
def post_create_request(request: Request,
                        course: str = Form(...),
                        date: str = Form(...),
                        payment: str = Form(...)):
    user_id = request.session.get("user_id")
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    with get_db() as conn:
        conn.execute("insert into requests (user_id, course_name, date_start, payment_method) values (?,?,?,?)", (user_id, course, date, payment)) #подсмотрела
    return RedirectResponse(url="/profile", status_code=302)

@app.get("/admin")
def get_admin(request: Request):
    user_id = request.session.get("admin") #вписала юзера вместо админа
    if not user_id:
        return RedirectResponse(url="/login", status_code=302)
    with get_db() as conn:
        request_list = conn.execute("select requests.*, users.login, users.fio from requests , users where users.id = requests.user_id").fetchall() #наделала ошибок, поэтому подсмотрела
    return templates.TemplateResponse("admin.html", {"request": request, "requests": request_list})