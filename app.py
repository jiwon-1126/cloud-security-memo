import os, time, secrets, hmac, hashlib, uuid, re
from functools import wraps
from contextlib import contextmanager
from urllib.parse import urlsplit
import jwt, pymysql
from flask import Flask, request, jsonify, g, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

DDL = [
'''CREATE TABLE IF NOT EXISTS users (id BIGINT PRIMARY KEY AUTO_INCREMENT, username VARCHAR(50) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, student_name VARCHAR(100) NOT NULL, github_id VARCHAR(100) NOT NULL) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS memos (id BIGINT PRIMARY KEY AUTO_INCREMENT, user_id BIGINT NOT NULL, content TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS request_nonces (user_id BIGINT NOT NULL, nonce CHAR(36) NOT NULL, token_jti CHAR(36) NOT NULL, expires_at BIGINT NOT NULL, PRIMARY KEY(user_id,nonce), INDEX(expires_at), FOREIGN KEY(user_id) REFERENCES users(id)) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS login_limits (bucket CHAR(64) PRIMARY KEY, window_id BIGINT NOT NULL, attempts INT NOT NULL) ENGINE=InnoDB''',
'''CREATE TABLE IF NOT EXISTS revoked_tokens (jti CHAR(36) PRIMARY KEY, expires_at BIGINT NOT NULL, INDEX(expires_at)) ENGINE=InnoDB''']

def create_app(config=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.update(MAX_CONTENT_LENGTH=16384, PUBLIC_ORIGIN=os.getenv('PUBLIC_ORIGIN','http://localhost:5000'), COOKIE_SECURE=os.getenv('COOKIE_SECURE','false').lower()=='true', JWT_SECRET=os.getenv('JWT_SECRET',''), CSRF_SECRET=os.getenv('CSRF_SECRET',''), TEST_USER_PASSWORD=os.getenv('TEST_USER_PASSWORD',''), DB_HOST=os.getenv('DB_HOST','127.0.0.1'), DB_PORT=int(os.getenv('DB_PORT','3306')), DB_USER=os.getenv('DB_USER','memo'), DB_PASSWORD=os.getenv('DB_PASSWORD',''), DB_NAME=os.getenv('DB_NAME','memo'))
    if config: app.config.update(config)
    for k in ('JWT_SECRET','CSRF_SECRET'):
        if len(app.config[k].encode())<32: raise RuntimeError(k+' must be at least 32 bytes')
    if app.config['JWT_SECRET']==app.config['CSRF_SECRET']: raise RuntimeError('Use different secrets')
    if app.config['PUBLIC_ORIGIN'].startswith('https://') and not app.config['COOKIE_SECURE']: raise RuntimeError('HTTPS requires secure cookies')
    c=app.config
    @contextmanager
    def db():
        conn=pymysql.connect(host=c['DB_HOST'],port=c['DB_PORT'],user=c['DB_USER'],password=c['DB_PASSWORD'],database=c['DB_NAME'],charset='utf8mb4',cursorclass=pymysql.cursors.DictCursor,connect_timeout=3,read_timeout=5,write_timeout=5)
        try:
            with conn.cursor() as cur: yield cur
            conn.commit()
        except Exception:
            conn.rollback(); raise
        finally: conn.close()
    def init():
        if not c['TEST_USER_PASSWORD']: raise RuntimeError('TEST_USER_PASSWORD required for initialization')
        with db() as cur:
            cur.execute("SELECT GET_LOCK('cloud_security_memo_init', 20) AS acquired")
            if cur.fetchone()['acquired']!=1: raise RuntimeError('DB init lock unavailable')
            for sql in DDL: cur.execute(sql)
            cur.execute('INSERT INTO users(username,password_hash,student_name,github_id) VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE username=username',('tester',generate_password_hash(c['TEST_USER_PASSWORD']),'성지원','jiwoninnuk'))
        # Connection close releases advisory lock after commit.
    app.cli.command('init-db')(init)
    app.extensions['init_db']=init
    def error(msg,status): return jsonify(error=msg),status
    def csrf_for(value): return hmac.new(c['CSRF_SECRET'].encode(),value.encode(),hashlib.sha256).hexdigest()
    def origin_ok(): return request.headers.get('Origin')==c['PUBLIC_ORIGIN']
    def csrf_ok(value): return hmac.compare_digest(request.headers.get('X-CSRF-Token',''),csrf_for(value))
    def cookie(resp,name,value,age):
        resp.set_cookie(name,value,max_age=age,httponly=True,secure=c['COOKIE_SECURE'],samesite='Lax',path='/')
    def auth(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            try:
                p=jwt.decode(request.cookies.get('access_token',''),c['JWT_SECRET'],algorithms=['HS256'],issuer='cloud-memo',audience='cloud-memo-web',options={'require':['sub','iat','exp','jti','iss','aud']})
                uid=int(p['sub']); uuid.UUID(p['jti'])
            except (jwt.InvalidTokenError,ValueError,TypeError): return error('로그인이 필요합니다.',401)
            with db() as cur:
                cur.execute('SELECT id,student_name,github_id FROM users WHERE id=%s',(uid,)); user=cur.fetchone()
                cur.execute('SELECT jti FROM revoked_tokens WHERE jti=%s',(p['jti'],)); revoked=cur.fetchone()
            if not user or revoked: return error('로그인이 필요합니다.',401)
            g.user=user; g.token=p
            return fn(*a,**kw)
        return wrapped
    def mutation(fn):
        @wraps(fn)
        def wrapped(*a,**kw):
            if not origin_ok() or not csrf_ok('auth:'+g.token['jti']): return error('CSRF 검증 실패',403)
            return fn(*a,**kw)
        return wrapped
    def payload():
        v=request.get_json(silent=True); return v if isinstance(v,dict) else {}
    def consume(cur):
        nonce=request.headers.get('X-Request-Nonce',''); ts=request.headers.get('X-Request-Timestamp','')
        try:
            if str(uuid.UUID(nonce))!=nonce: raise ValueError()
            timestamp=int(ts)
            if abs(int(time.time())-timestamp)>60: raise ValueError()
        except (ValueError,TypeError): return error('유효하지 않은 nonce 또는 timestamp',400)
        try:
            cur.execute('INSERT INTO request_nonces(user_id,nonce,token_jti,expires_at) VALUES (%s,%s,%s,%s)',(g.user['id'],nonce,g.token['jti'],int(time.time())+3700))
        except pymysql.err.IntegrityError as e:
            if e.args[0]==1062: return error('중복 요청',409)
            raise
    @app.after_request
    def headers(resp):
        resp.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        resp.headers['X-Content-Type-Options']='nosniff'; resp.headers['Referrer-Policy']='no-referrer'; resp.headers['Cache-Control']='no-store'
        if c['COOKIE_SECURE']: resp.headers['Strict-Transport-Security']='max-age=31536000'
        return resp
    @app.errorhandler(pymysql.MySQLError)
    def db_error(e):
        app.logger.error('Database operation failed: %s',type(e).__name__); return error('서비스 일시 오류',503)
    @app.get('/')
    def index(): return render_template('index.html')
    @app.get('/api/login-csrf')
    def login_csrf():
        seed=secrets.token_urlsafe(32); resp=jsonify(csrf_token=csrf_for('login:'+seed)); cookie(resp,'login_seed',seed,300); return resp
    @app.post('/api/login')
    def login():
        seed=request.cookies.get('login_seed','')
        if not seed or not origin_ok() or not csrf_ok('login:'+seed): return error('CSRF 검증 실패',403)
        p=payload(); username=p.get('username'); password=p.get('password')
        if not isinstance(username,str) or not isinstance(password,str) or not 1<=len(username)<=50 or not 1<=len(password)<=256: return error('잘못된 입력',400)
        # Shared fixed-window account and source limits; do not trust arbitrary forwarded headers.
        window=int(time.time())//60
        with db() as cur:
            counts=[]
            for value in sorted(['account:'+username.lower(),'source:'+(request.remote_addr or '')]):
                bucket=hashlib.sha256(value.encode()).hexdigest()
                cur.execute('INSERT INTO login_limits(bucket,window_id,attempts) VALUES (%s,%s,1) ON DUPLICATE KEY UPDATE attempts=IF(window_id=VALUES(window_id),attempts+1,1),window_id=VALUES(window_id)',(bucket,window))
                cur.execute('SELECT attempts FROM login_limits WHERE bucket=%s',(bucket,)); counts.append(cur.fetchone()['attempts'])
            if max(counts)>10: return error('로그인 시도 제한',429)
            cur.execute('SELECT * FROM users WHERE username=%s',(username,)); user=cur.fetchone()
        if not user or not check_password_hash(user['password_hash'],password): return error('아이디 또는 비밀번호가 올바르지 않습니다.',401)
        now=int(time.time()); jti=str(uuid.uuid4()); token=jwt.encode(dict(sub=str(user['id']),iat=now,exp=now+1800,jti=jti,iss='cloud-memo',aud='cloud-memo-web'),c['JWT_SECRET'],algorithm='HS256')
        resp=jsonify(message='로그인 성공',student_name=user['student_name'],github_id=user['github_id']); cookie(resp,'access_token',token,1800); resp.delete_cookie('login_seed',path='/',secure=c['COOKIE_SECURE'],httponly=True,samesite='Lax'); return resp
    @app.get('/api/csrf')
    @auth
    def csrf(): return jsonify(csrf_token=csrf_for('auth:'+g.token['jti']))
    @app.get('/api/profile')
    @auth
    def profile(): return jsonify(student_name=g.user['student_name'],github_id=g.user['github_id'])
    @app.get('/api/memos')
    @auth
    def memos():
        with db() as cur:
            cur.execute('SELECT m.id,u.student_name AS author,m.content,m.created_at FROM memos m JOIN users u ON u.id=m.user_id ORDER BY m.id DESC LIMIT 200'); return jsonify(cur.fetchall())
    @app.post('/api/memos')
    @auth
    @mutation
    def create_memo():
        content=payload().get('content')
        if not isinstance(content,str) or not content.strip() or len(content)>2000: return error('메모는 1~2000자',400)
        with db() as cur:
            fail=consume(cur)
            if fail: return fail
            cur.execute('INSERT INTO memos(user_id,content) VALUES (%s,%s)',(g.user['id'],content)); mid=cur.lastrowid
        return jsonify(message='메모 등록 완료',memo=dict(id=mid,author=g.user['student_name'],content=content)),201
    @app.post('/api/logout')
    @auth
    @mutation
    def logout():
        with db() as cur:
            fail=consume(cur)
            if fail: return fail
            cur.execute('INSERT IGNORE INTO revoked_tokens(jti,expires_at) VALUES (%s,%s)',(g.token['jti'],g.token['exp']))
        resp=jsonify(message='로그아웃 완료'); resp.delete_cookie('access_token',path='/',secure=c['COOKIE_SECURE'],httponly=True,samesite='Lax'); return resp
    @app.get('/health')
    def health():
        with db() as cur: cur.execute('SELECT 1 FROM users LIMIT 1')
        return jsonify(status='ok')
    return app
