"""创建管理员账号 — 幂等（已存在则跳过）"""
import hashlib
import os
os.environ["LB_DATABASE_URL"] = os.environ.get("LB_DATABASE_URL", "sqlite:///./dev.db")

from app.core.database import SessionLocal, init_db
from app.models.admin_user import AdminUser

init_db()

db = SessionLocal()

admin = db.query(AdminUser).filter_by(username="admin").first()
if admin:
    print("管理员账号已存在，跳过")
else:
    pwd_hash = hashlib.sha256("admin123".encode()).hexdigest()
    admin = AdminUser(username="admin", password_hash=pwd_hash, role="admin")
    db.add(admin)
    db.commit()
    print("✅ 管理员账号创建成功: admin / admin123")

db.close()
