# AI 프롬프트 엔지니어링 일지
- 응시자: 성지원
- GitHub: jiwoninnuk
- 날짜: 2026-11-26
- 단계: 1. 레거시 분석 및 설계

## 사용한 프롬프트
> 첨부된 기존 레거시 소스 코드를 먼저 분석한다. 기존 코드의 인증 방식, 데이터 저장 방식, API 구조, 보안 취약점, 장애 가능성을 정리한다. 기존 기능과 API 호환성을 최대한 유지하면서 개선 방향을 제시한다. Nginx, Flask, MariaDB의 3-Tier 아키텍처를 설계한다. Web-WAS 네트워크와 WAS-DB 네트워크를 분리한다. WAS를 복수 레플리카로 운영하고 Rolling Update 및 Health Check를 적용할 수 있도록 설계한다. 이번 단계에서는 전체 코드를 한꺼번에 생성하지 말고 설계와 요구사항 분석을 우선한다.

## 기존 요구사항 및 추가 제약
| 기존 요구사항 | 추가 제약 | 이유 | 제안 |
|---|---|---|---|
| 토큰 인증과 웹 보안 | 공유 서명 키, DB 기반 nonce, 원자적 중복 방지 | 여러 WAS에서 일관된 인증 및 재전송 방어 | JWT, HttpOnly, CSRF 토큰, MariaDB UNIQUE 제약 |
| 3-Tier 분리 | Web/WAS와 WAS/DB 별도 overlay, DB 포트 미공개 | Web의 직접 DB 접근 차단 | internal backend, WAS만 양쪽 연결 |
| 자동 배포 | WAS 2 replicas, start-first, 헬스체크, SHA 태그 | 교체 중 요청 실패와 포트 충돌 최소화 | Swarm rolling update 및 롤백 |
| 시간 제한 | 120분, 기존 API 유지, Kubernetes 제외 | 구현 범위 통제 | Flask/Gunicorn, Nginx, MariaDB |

## 실제 분석
- 대상: app(20261126-005806).py
- USERS/MEMOS 전역 변수 사용, 평문 비밀번호, 서명 없는 session_user 쿠키.
- 메모 출력에 innerHTML 사용, CSRF 및 nonce 검증 없음.
- Flask 개발 서버 debug=True.
- Python compile() 정적 검사 결과: line 43, `unindent does not match any outer indentation level`. 첫 오류를 메모리에서만 수정한 후 line 67에서 `expected an indented block` 확인. 원본 파일은 수정하지 않았다.
- 위 결과는 설계 분석 및 실제 정적 검사 기록이며, 실행 중 발생한 컨테이너 오류는 아니다.

## 검증 필요
- JWT 위조/만료 거부, 쿠키 속성, CSRF 및 nonce 중복 차단, XSS 안전 출력.
- DB 초기화와 재생성 후 영속성, Nginx→DB 차단 및 WAS→DB 허용.
- 실제 GitHub Actions 배포 및 배포 중 요청 실패 측정.
- 단일 VM/DB/Nginx의 SPOF는 남는다.

## 기록 상태
현재 1단계 설계만 완료. 위 세 가지 고도화 방향은 후보이며 실제 후속 프롬프트, 코드 diff, 테스트 결과를 추가해야 완료 사례로 인정할 수 있다. 실제 트러블슈팅 해결 사례는 아직 0건이다.

## 2단계 — 백엔드 구현 (2026-11-26)
- 실제 사용자 요청: Flask API, MariaDB 자동 초기화, JWT 쿠키, XSS/CSRF/replay 방어, pytest, 일지 업데이트. 직전 사용자 정정에 따라 복사 프롬프트의 GitHub ID를 jiwoninnuk으로 수정했다.
- 기존 요구: 메모리 기반 인증 및 저장을 개선. 추가 제약: JWT 서명 알고리즘 고정 및 exp/iss/aud 검증, HttpOnly 쿠키, 로그인 포함 Origin/CSRF 검증, DB 기반 nonce와 메모를 원자적으로 저장, 공유 로그인 제한, 동시 초기화 잠금.
- 이유: 사용자명 쿠키는 위조 가능하며 HttpOnly는 브라우저가 자동으로 쿠키를 전송하는 CSRF를 막지 못한다. WAS 메모리 nonce는 복제 시 공유되지 않는다. UNIQUE 및 InnoDB 트랜잭션으로 동일 요청 중복 저장을 방지하도록 구현했다. GET_LOCK으로 초기화 경쟁을 직렬화하고 기존 계정은 덮어쓰지 않는다.
- 변경 파일: app.py, init_db.py, wsgi.py, start.sh, templates/index.html, static/app.js, tests/test_security.py, requirements.txt, .env.example.
- 설계 변경: 로그인 전 CSRF 발급 API 추가, 로그아웃 토큰 폐기 테이블 추가(완전 stateless는 아님), 로그인 제한 DB 테이블 추가. 기존 초기 시스템 메모는 신규 DB에 이관하지 않음.
- 실제 검사: Python compileall 성공. pip install -r requirements.txt 실패 (ERROR: Could not find a version that satisfies the requirement Flask<4,>=3.1). 환경 제약이며 앱 구축 오류 해결 사례로 집계하지 않는다. MariaDB/HTTP/브라우저 테스트 미검증.
