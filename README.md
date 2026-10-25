# NiceGUI TXT Reader

개인용 TXT 북리더입니다. NiceGUI로 UI를 구성하고 Render에 배포하며, 책과 설정은 Neon PostgreSQL에 저장합니다.

## V1.0 주요 기능
- 숫자 4자리 PIN 로그인, 로그인 세션 12시간
- PC TXT 불러오기 (최대 3 MiB, UTF-8 / CP949)
- 새 문서 작성, 읽기/수정 모드, 전체 복사
- NeonDB 책별 UUID 저장 / 수정 / 불러오기 / 삭제
- MY ARCHIVE 제목순 정렬, 선택 행 강조, 삭제 확인
- 읽기 모드에서 DB 저장 시 책별 읽던 위치 저장
- 수정 모드에서 DB 저장 시 파일명/본문만 저장하고 기존 위치 유지
- 바탕색/글자색 사용자 지정, 라이트/다크/기본색
- 글자 크기와 줄 간격 저장 및 복원

## 기본 테마
- 라이트: 배경 `#ECEFE6`, 글자 `#2A2A2A`
- 다크: 배경 `#22252A`, 글자 `#E5E0D8`
- 기본색: 사용자가 지정한 바탕색/글자색 조합

## 저장 구조
### documents
책마다 한 행을 사용합니다.
- `id` UUID
- `filename`
- `content`
- `reading_position` 0~1 상대 스크롤 위치
- `has_saved_position` 위치 저장 여부
- `created_at`, `updated_at`

### reader_settings
모든 책에 공통인 화면 설정을 JSONB로 저장합니다.

## 읽던 위치 정책
- 읽기 모드에서 **DB 저장하기**를 눌렀을 때만 현재 위치를 저장합니다.
- 수정 모드 저장은 본문/파일명만 저장하고 기존 읽기 위치는 바꾸지 않습니다.
- 저장하지 않고 다른 책으로 이동하면 임시 스크롤 위치는 버립니다.
- 책을 다시 열면 DB에 마지막으로 저장한 위치를 복원합니다.
- MY ARCHIVE는 책을 열 때 전체 재생성하지 않고 선택 행만 갱신합니다. 이는 NiceGUI 클릭 slot을 유지해 위치 복원이 안정적으로 동작하도록 하기 위함입니다.

## Render 환경변수
- `APP_PASSWORD_HASH`: Argon2id PIN 해시
- `STORAGE_SECRET`: NiceGUI 사용자 세션 서명 키
- `DATABASE_URL`: Neon PostgreSQL 연결 문자열

비밀번호, 해시, 세션 비밀키, DB 연결 문자열은 GitHub에 커밋하지 않습니다.

PIN/세션 값 생성:

```bash
pip install argon2-cffi
python scripts/generate_auth_secrets.py
```

## 실행
```bash
pip install -r requirements.txt
python main.py
```

Render에서는 `render.yaml` 설정을 사용할 수 있습니다.
