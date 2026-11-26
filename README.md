# Cloud Security Memo — 2단계
성지원 / jiwoninnuk. 기존 API 경로 유지. 기존 메모는 메모리 데이터였으므로 자동 이전되지 않으며 신규 DB는 빈 게시판으로 시작한다.

## 로컬 실행 (Mac, Docker Desktop 또는 기존 MariaDB)
```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_hex(32)); print(secrets.token_hex(32))'
```
.env에 위 두 값을 각각 JWT_SECRET, CSRF_SECRET에 설정하고 DB_PASSWORD와 TEST_USER_PASSWORD(평가용 test1234!)를 직접 입력한다. PUBLIC_ORIGIN은 실제 브라우저 주소와 정확히 일치해야 한다.
로컬 DB가 없다면 아래 명령으로 개발 전용 DB를 띄운다(호스트 loopback만 공개, 4단계 운영 격리와 별개). 비밀번호는 직접 입력한다.
```sh
read -s 'DB_PASSWORD?DB password: '
export DB_PASSWORD
docker run -d --name memo-dev-db -p 127.0.0.1:3306:3306 -e MARIADB_RANDOM_ROOT_PASSWORD=1 -e MARIADB_DATABASE=memo -e MARIADB_USER=memo -e MARIADB_PASSWORD="$DB_PASSWORD" -v memo-dev-data:/var/lib/mysql mariadb:11.4
./start.sh
```
http://localhost:5000 접속. 위 read 문법은 macOS zsh 기준. 이미 DB가 있다면 컨테이너 생성 생략. DB 사용자에게 해당 스키마의 CREATE, SELECT, INSERT, UPDATE, DELETE 권한 필요(초기화 후 운영에서는 별도 초기화 계정으로 CREATE 분리 권장). root 계정으로 앱 실행 금지.

## 테스트
별도 테스트 DB를 사용하고 .env의 DB_NAME 등 설정을 변경한다. `RUN_DB_TESTS=1 python -m pytest -q` 실행. 테스트는 메모 및 로그인 제한 데이터를 남기므로 운영 DB 사용 금지. 반복 실행 시 분당 제한에 걸리면 다음 분에 실행. 브라우저에서 XSS 문자열이 텍스트로 표시되는지 추가 확인.

## 보안 설계
로그인 전에 GET /api/login-csrf로 사전 인증 CSRF 토큰을 받는다. 모든 POST에 실제 Origin과 X-CSRF-Token 헤더 필요. 인증 후 /api/csrf 사용. 메모 작성 및 로그아웃에 X-Request-Nonce(UUID), X-Request-Timestamp(Unix seconds, ±60초) 필요. JWT는 30분 만료, HS256 고정, issuer/audience 검증. 로그아웃은 DB 폐기 목록을 사용하므로 인증 서명 검증은 stateless이나 폐기 여부 확인은 stateful이다. nonce 및 메모 삽입은 동일 트랜잭션. nonce 기록은 자동 삭제하지 않으므로 운영 시 만료 데이터 정리 작업 필요. 로그인 제한은 계정 및 연결 IP별 분당 10회; Nginx 뒤에서는 연결 IP가 프록시로 합쳐질 수 있으므로 신뢰된 프록시 설정 또는 Nginx rate limit을 4단계에서 추가한다. HTTP 평가 환경은 COOKIE_SECURE=false; HTTPS는 true 필수. HTTP는 도청 방어 불가. 탈취 JWT로 새 요청을 만드는 행위까지 방지하지는 못한다.

## 검증 상태
Python 문법 검사 완료. 이 환경에는 Docker/MariaDB가 없고 Flask/PyMySQL 설치 실패로 API/DB/브라우저 통합 테스트 미실행. Docker Swarm, Nginx, CI/CD는 후속 단계.
