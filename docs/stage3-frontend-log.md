# 3단계 프론트엔드 개선 기록 (2026-11-26)
- 기존 코드 직접 확인: app.py의 login-csrf, login, csrf, profile, memos, logout 규격과 CSP 확인. 기존 JS에는 작성 시간 표시와 인증 만료 화면 전환이 부족했다.
- 추가 제약: 외부 라이브러리 및 인라인 스크립트/스타일 배제, DB 프로필만 표시, HTTP IP 접속에서도 안전한 난수 UUID fallback, 401 응답 시 화면 및 민감한 DOM 정보 초기화, 중복 클릭 제한.
- 변경: templates/index.html, static/app.js, static/style.css. 백엔드 및 DB 설정 변경 없음.
- 이유: CSP 완화 없이 디자인 구현, 실제 API 응답과 일치, XSS 안전한 텍스트 출력 유지, 인증 만료 처리 및 메모 작성 결과 구분.
- 검증: node --check static/app.js 통과. 실제 MariaDB/Flask 통합 테스트는 로컬 서버에서 수행 필요.
- 증빙: 로그인, DB 프로필, 메모 작성 시간, 새로고침 후 유지, 로그아웃, XSS 텍스트 표시, 쿠키 속성, 비인증 API 401.
