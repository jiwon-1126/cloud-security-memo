## 5단계 AI 활용 고도화 — CI/CD
- 기존 요구사항: main push 후 이미지 빌드 및 SSH 배포.
- 실제 환경 제약: ARM64 단일 Ubuntu Swarm, LAN 사설 IP, 공개 GitHub 저장소, 기존 DB와 메모 보존.
- 추가 조건: hosted runner에서 Tailscale 사설 접속, SSH 호스트 키 검증, CI 전용 MariaDB에서 pytest 실행(RUN_DB_TESTS=1), 테스트 실패 시 build/deploy 중단.
- latest 대신 commit SHA 태그 및 digest 고정으로 배포 이미지 식별성 확보.
- 전체 stack 재배포/컨테이너 종료 대신 WAS 서비스만 start-first rolling update, 2 replicas, 병렬 1, 5초 delay, 300초 monitor, 실패 rollback.
- workflow concurrency cancel-in-progress=false와 서버 flock으로 중복 배포 방지.
- GitHub Secrets 및 배포용 SSH 키로 실제 자격 증명을 코드에서 분리. Docker 그룹 권한은 root 수준이므로 별도 제한 계정은 향후 개선.
- HTTP 상태, curl 종료 코드, UTC 시각, 배포 전후 digest, 실패 수 기록. 관측 실패 시 이전 이미지 복원 시도. 샘플링 기반이며 절대적 무중단 보장은 아님.
- 검증: YAML 파싱, Bash 문법 검사 완료. 실제 CI/CD 및 rollback, Tailscale, 브라우저 데이터 유지 검증은 미수행. 실제 결과와 Git commit을 사용자 실행 후 추가할 것.

- Cloudflare Service Token 없이 배포하기 위해 private 저장소의 macOS self-hosted runner를 배포 job에만 사용하도록 변경. 테스트와 빌드는 hosted runner 유지. 실제 실행 및 결과는 사용자 검증 후 기록.

## Pull CD 변경
- 사용자 요청으로 self-hosted runner, Tailscale, Cloudflare Service Token 제거.
- GitHub-hosted runner에서 테스트 통과 후 SHA 및 main-ready 발행, 서버 timer에서 digest로 배포.
- SSH 배포 요구사항 미충족, GitHub Actions 성공은 이미지 발행 성공만 의미. 배포 로그는 서버에서 확인.
- 실제 배포, HTTP 실패 횟수, 롤백, 데이터 유지 검증은 미수행.
