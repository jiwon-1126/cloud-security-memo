import time
import pymysql
from app import create_app

app = create_app()
for attempt in range(20):
    try:
        app.extensions['init_db']()
        print('DB initialized', flush=True)
        break
    except pymysql.OperationalError as exc:
        if attempt == 19:
            raise
        print(f'DB initialization retry {attempt + 1}/19 ({type(exc).__name__})', flush=True)
        time.sleep(min(2 ** (attempt + 1), 10))
