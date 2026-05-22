import sqlite3
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR.parent / "frontend"
DB_PATH = BASE_DIR / "dorm_repair.db"
ALLOWED_STATUS = {"待处理", "处理中", "已完成"}

app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ok(data=None, message="success"):
    return jsonify({"success": True, "message": message, "data": data or {}})


def fail(message, status=400):
    return jsonify({"success": False, "message": message}), status


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,OPTIONS"
    return response


@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "login.html")


@app.route("/api/health")
def health():
    return ok({"time": now_text()}, "server is running")


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not username or not password:
        return fail("用户名和密码不能为空")

    conn = get_conn()
    user = conn.execute(
        "SELECT id, username, role, dormitory, phone FROM user WHERE username = ? AND password = ?",
        (username, password),
    ).fetchone()
    conn.close()

    if not user:
        return fail("用户名或密码错误", 401)

    return ok(dict(user), "登录成功")


@app.route("/api/categories", methods=["GET"])
def categories():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, description FROM repair_category ORDER BY id"
    ).fetchall()
    conn.close()
    return ok([dict(row) for row in rows], "查询成功")


@app.route("/api/orders", methods=["POST"])
def create_order():
    data = request.get_json(silent=True) or {}
    student_id = data.get("student_id")
    category_id = data.get("category_id")
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()

    if not student_id:
        return fail("student_id 不能为空")
    if not category_id:
        return fail("category_id 不能为空")
    if not title:
        return fail("报修标题不能为空")

    conn = get_conn()
    category = conn.execute(
        "SELECT id FROM repair_category WHERE id = ?", (category_id,)
    ).fetchone()
    if not category:
        conn.close()
        return fail("报修类别不存在")
        
    current_time = now_text()
    cursor = conn.execute(
        """
        INSERT INTO repair_order (student_id, category_id, title, description, status, create_time, update_time)
        VALUES (?, ?, ?, ?, '待处理', ?, ?)
        """,
        (student_id, category_id, title, description, current_time, current_time),
    )
    order_id = cursor.lastrowid
    conn.execute(
        """
        INSERT INTO repair_log (order_id, operator_id, action, remark, operate_time)
        VALUES (?, ?, ?, ?, ?)
        """,
        (order_id, student_id, "创建工单", "学生提交报修", current_time),
    )
    conn.commit()
    conn.close()
    return ok({"order_id": order_id}, "报修提交成功")


@app.route("/api/orders/my", methods=["GET"])
def my_orders():
    student_id = request.args.get("student_id", type=int)
    if not student_id:
        return fail("student_id 不能为空")

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT o.id, o.title, o.description, o.status, o.create_time, o.update_time, o.finish_time,
               c.name AS category_name
        FROM repair_order o
        JOIN repair_category c ON o.category_id = c.id
        WHERE o.student_id = ?
        ORDER BY o.id DESC
        """,
        (student_id,),
    ).fetchall()
    conn.close()
    return ok([dict(row) for row in rows], "查询成功")


@app.route("/api/orders/all", methods=["GET"])
def all_orders():
    role = (request.args.get("role") or "").strip()
    if role != "admin":
        return fail("只有管理员可以查看全部工单", 403)

    conn = get_conn()
    rows = conn.execute(
        """
        SELECT o.id, o.title, o.description, o.status, o.create_time, o.update_time, o.finish_time,
               c.name AS category_name, u.username AS student_name, u.dormitory
        FROM repair_order o
        JOIN repair_category c ON o.category_id = c.id
        JOIN user u ON o.student_id = u.id
        ORDER BY o.id DESC
        """
    ).fetchall()
    conn.close()
    return ok([dict(row) for row in rows], "查询成功")


@app.route("/api/orders/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id: int):
    data = request.get_json(silent=True) or {}
    operator_id = data.get("operator_id")
    operator_role = (data.get("operator_role") or "").strip()
    status = (data.get("status") or "").strip()
    remark = (data.get("remark") or "").strip()

    if operator_role != "admin":
        return fail("只有管理员可以修改工单状态", 403)
    if status not in ALLOWED_STATUS:
        return fail("状态不合法")

    conn = get_conn()
    order = conn.execute(
        "SELECT id, status FROM repair_order WHERE id = ?",
        (order_id,),
    ).fetchone()
    if not order:
        conn.close()
        return fail("工单不存在", 404)

    current_time = now_text()
    finish_time = current_time if status == "已完成" else None
    conn.execute(
        """
        UPDATE repair_order
        SET status = ?, update_time = ?, finish_time = ?
        WHERE id = ?
        """,
         (status, current_time, finish_time, order_id),
    )
    conn.execute(
        """
        INSERT INTO repair_log (order_id, operator_id, action, remark, operate_time)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            order_id,
            operator_id or 0,
            "状态更新",
            remark or f"工单状态修改为：{status}",
            current_time,
        ),
    )
    conn.commit()
    conn.close()
    return ok({"order_id": order_id, "status": status}, "状态更新成功")


if __name__ == "__main__":
    app.run(debug=True)