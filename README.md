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
