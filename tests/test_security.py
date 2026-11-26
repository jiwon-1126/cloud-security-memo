import os,time,uuid,jwt,pytest
from app import create_app

@pytest.fixture
def client():
    if os.getenv('RUN_DB_TESTS')!='1': pytest.skip('Requires dedicated MariaDB test database')
    app=create_app({'TESTING':True})
    app.extensions['init_db']()
    return app,app.test_client()

def login(app,c,pw='test1234!'):
    t=c.get('/api/login-csrf').json['csrf_token']
    return c.post('/api/login',json={'username':'tester','password':pw},headers={'Origin':app.config['PUBLIC_ORIGIN'],'X-CSRF-Token':t})

def headers(app,c):
    return {'Origin':app.config['PUBLIC_ORIGIN'],'X-CSRF-Token':c.get('/api/csrf').json['csrf_token'],'X-Request-Nonce':str(uuid.uuid4()),'X-Request-Timestamp':str(int(time.time()))}

def test_security(client):
    app,c=client
    assert c.get('/api/memos').status_code==401
    assert c.post('/api/login',json={}).status_code==403
    assert login(app,c,'wrong').status_code==401
    r=login(app,c); assert r.status_code==200
    cookie=' '.join(r.headers.getlist('Set-Cookie')); assert 'HttpOnly' in cookie and 'SameSite=Lax' in cookie
    assert c.get('/api/profile').json=={'student_name':'성지원','github_id':'jiwoninnuk'}
    assert c.post('/api/memos',json={'content':'test'}).status_code==403
    h=headers(app,c); bad=dict(h,**{'X-CSRF-Token':'invalid'}); assert c.post('/api/memos',json={'content':'test'},headers=bad).status_code==403
    stale=dict(h,**{'X-Request-Timestamp':str(int(time.time())-120)}); assert c.post('/api/memos',json={'content':'test'},headers=stale).status_code==400
    text='<img src=x onerror=alert(1)>'
    assert c.post('/api/memos',json={'content':text},headers=h).status_code==201
    assert c.post('/api/memos',json={'content':text},headers=h).status_code==409
    assert any(m['content']==text for m in c.get('/api/memos').json)
    assert 'script-src' in c.get('/').headers['Content-Security-Policy']
    assert c.post('/api/logout',json={},headers=headers(app,c)).status_code==200
    assert c.get('/api/memos').status_code==401

def test_jwt(client):
    app,c=client
    assert login(app,c).status_code==200
    token=c.get_cookie('access_token').value
    p=jwt.decode(token,app.config['JWT_SECRET'],algorithms=['HS256'],issuer='cloud-memo',audience='cloud-memo-web')
    c.set_cookie('access_token',jwt.encode(p,'x'*40,algorithm='HS256'))
    assert c.get('/api/profile').status_code==401
    p['exp']=int(time.time())-1
    c.set_cookie('access_token',jwt.encode(p,app.config['JWT_SECRET'],algorithm='HS256'))
    assert c.get('/api/profile').status_code==401
