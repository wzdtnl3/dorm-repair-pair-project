import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "dorm_repair.db"


def create_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            phone TEXT,
            dormitory TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS repair_category (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS repair_order (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT NOT NULL DEFAULT '待处理',
            create_time TEXT NOT NULL,
            update_time TEXT NOT NULL,
            finish_time TEXT,
            FOREIGN KEY(student_id) REFERENCES user(id),
            FOREIGN KEY(category_id) REFERENCES repair_category(id)
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS repair_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            operator_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            remark TEXT,
            operate_time TEXT NOT NULL,
            FOREIGN KEY(order_id) REFERENCES repair_order(id),
            FOREIGN KEY(operator_id) REFERENCES user(id)
        )
        """
    )


def seed_data(cursor: sqlite3.Cursor) -> None:
    cursor.executemany(
        """
        INSERT OR IGNORE INTO user (username, password, role, phone, dormitory)
        VALUES (?, ?, ?, ?, ?)
        """,
        [
            ("admin", "123456", "admin", "18800000000", "办公室"),
            ("stu001", "123456", "student", "18811110001", "1-201"),
            ("stu002", "123456", "student", "18811110002", "1-202"),
        ],
    )

    cursor.executemany(
        """
        INSERT OR IGNORE INTO repair_category (name, description)
        VALUES (?, ?)
        """,
        [
            ("水电报修", "宿舍内用水用电问题"),
            ("网络报修", "校园网或路由器问题"),
            ("家具报修", "桌椅、门锁、床铺等设施问题"),
        ],
    )


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    create_tables(cursor)
    seed_data(cursor)
    conn.commit()
    conn.close()
    print(f"数据库初始化完成：{DB_PATH}")


if __name__ == "__main__":
    main()