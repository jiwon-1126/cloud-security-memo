import time
from app import create_app
import pymysql
app=create_app()
for attempt in range(20):
    try:
        app.extensions['init_db'](); print('DB initialized'); break
    except pymysql.OperationalError:
        if attempt==19: raise
        time.sleep(2)
