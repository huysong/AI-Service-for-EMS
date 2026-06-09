# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# 1. Tạo Async Engine kết nối tới PostgreSQL
engine = create_async_engine(
    settings.ASYNC_DATABASE_URL,
    echo=True, # Đặt True để SQLAlchemy in các câu lệnh SQL ra terminal khi debug (khi chạy thật nên tắt)
    pool_size=10,       # Số lượng kết nối tối đa giữ lại trong pool
    max_overflow=20     # Số lượng kết nối vượt mức cho phép khi quá tải
)

# 2. Tạo Session factory để sinh ra các phiên làm việc bất đồng bộ với DB
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# 3. Base class để các lớp Model (bảng biểu) kế thừa sau này
class Base(DeclarativeBase):
    pass

# 4. Dependency cấp Session cho các API Endpoint (Luôn đóng kết nối sau khi dùng xong)
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()