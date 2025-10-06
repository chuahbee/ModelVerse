# ModelVerse (Django eCommerce)

## Tech Stack
- Python 3.11+/Django 5.x
- SQLite(本地) / MySQL(生产)
- Static via `collectstatic` + (可选) WhiteNoise
- Media via `/media/` (Nginx/Apache or cPanel)

## Quickstart (Local)
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

## Env (.env 示例)
DEBUG=True
SECRET_KEY=change_me
ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
# 生产:
# DATABASE_URL=mysql://USER:PASSWORD@HOST:3306/DBNAME

## Static & Media
python manage.py collectstatic  # 生产
MEDIA_ROOT=...  STATIC_ROOT=...

## Deploy (cPanel 概要)
- Passenger + `passenger_wsgi.py`
- venv 安装依赖
- 设置 `DJANGO_SETTINGS_MODULE=myshopmall.settings_prod`
- 执行 `collectstatic` 与数据库迁移
