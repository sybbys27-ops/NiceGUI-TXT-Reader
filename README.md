# NiceGUI TXT Reader

Personal TXT book reader — initial NiceGUI UI milestone.

**Security warning:** This prototype has no login and no database connection. Do not upload private documents to a public Render deployment yet.

## Current features
- TXT upload from PC (up to 3 MiB, UTF-8 / CP949)
- Display file name, read/edit toggle, copy all
- Font size and background theme
- DB save/load buttons intentionally disabled until auth and Neon are ready

## Next steps
1. Argon2id password validation, protected routes and sessions.
2. Neon PostgreSQL: one UUID row per book; name, body, reading position.
3. Full DB operations, edit cancellation, appearance persistence.
4. Render deployment test.

## Run
```bash
pip install -r requirements.txt
python main.py
```
Open http://localhost:8080. Render Web Service can use `render.yaml`.
Never commit passwords, connection strings, or actual book text.

New and PC-loaded documents will INSERT a new UUID when saved. DB-loaded books will UPDATE by ID even when the filename changes. Copy/save-as is postponed to V1.1.


## 로그인 인증 설정 (feature/login-auth)

보안 기능은 개발 브랜치에서 시험 중입니다. 로그인/배포 검증 전에는 `main`으로 합치지 않습니다.

1. 로컬 PC에서 `pip install argon2-cffi`를 실행합니다.
2. `python scripts/generate_auth_secrets.py`를 실행하고, 숫자 4자리 PIN을 두 번 입력합니다. (보안 강도는 낮습니다.)
3. 출력되는 `APP_PASSWORD_HASH`와 `STORAGE_SECRET` 값을 Render 서비스의 **Environment**에 각각 입력합니다.
4. Render의 Branch를 `feature/login-auth`로 바꿔 재배포 후 로그인 화면을 확인합니다.
5. 테스트가 끝나면 기존 브랜치로 돌아가거나 이 브랜치를 PR로 병합합니다.

비밀번호, 비밀번호 해시, 세션 비밀키는 **절대로 GitHub에 커밋하지 마세요**. 둘 중 하나라도 비어 있으면 앱은 문서 화면 대신 초기 설정 안내를 표시합니다. 인증 세션은 최대 12시간입니다. 현재 로그인 실패 제한은 브라우저 연결 단위의 간단한 제한이며 공개 서비스에 대한 강력한 IP별 요청 제한을 대체하지 못합니다. 아직 Neon 저장 기능은 구현되지 않았습니다.

PIN 정책: 개인용 간편 로그인은 **숫자 4자리**만 허용합니다. 비밀번호 검증에는 Argon2id 해시를 계속 사용하며, 로그인 유지시간은 12시간입니다. 4자리 PIN은 10,000가지 조합뿐이라 공개 URL에서 무차별 대입에 취약할 수 있습니다. 현재의 연결별 시도 제한 외에 배포 전 IP/전체 요청 제한을 추가하는 것이 좋습니다.


## Neon DB 연결 (feature/neon-db)

Render Environment에 `DATABASE_URL`을 등록하세요. Neon의 pooled PostgreSQL connection string을 그대로 사용하며 GitHub에 공개하지 않습니다. `APP_PASSWORD_HASH`와 `STORAGE_SECRET`도 유지해야 합니다.

Render Branch를 `feature/neon-db`로 변경하면 앱은 첫 로그인 후 `documents` 테이블을 자동 생성합니다. 문서별 UUID를 기준으로 INSERT/UPDATE/DELETE하며, 우측 MY ARCHIVE 목록에서 선택 및 삭제할 수 있습니다. 글꼴 설정과 마지막 읽던 위치 저장은 다음 개발 단계입니다. **실제 DB에 연결해 실행 검증하기 전의 개발 기능입니다.**


## 읽기 위치 및 화면 설정 저장 (2026-10-25)

- 책의 스크롤 위치는 `documents.reading_position`에 0~1 사이의 비율로 저장합니다. 활성 책을 읽는 동안 약 3초 간격으로 변경 여부를 검사하며, 책 전환 및 로그아웃 시에도 저장을 시도합니다.
- 공통 테마, 배경색, 글자색, 글꼴 크기, 줄 간격은 `reader_settings` 테이블의 JSONB 한 행에 저장합니다. 다음 로그인/새로고침 시 복원합니다.
- 스크롤 저장은 브라우저 종료 직전의 마지막 수 초 동안 발생한 변경까지 반드시 보장하지는 않습니다. 위치 복원은 텍스트 영역의 상대 스크롤 비율을 이용하므로 폰트/창 크기 변경 시 정확한 문장 위치는 달라질 수 있습니다.
- Neon 연결 및 Render 실행 검증 전이므로 PR #3은 Draft로 유지합니다. 기존 문서 데이터 삭제/초기화는 하지 않습니다.
