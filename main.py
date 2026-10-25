"""Desktop-style NiceGUI TXT reader prototype. DB/login are not enabled yet."""
import inspect
import hmac
import time
import json
import logging
import os

from argon2 import PasswordHasher, exceptions as argon_errors
from nicegui import app, ui
import db

MAX_BYTES = 3 * 1024 * 1024
PASSWORD_HASH = os.getenv('APP_PASSWORD_HASH', '')
STORAGE_SECRET = os.getenv('STORAGE_SECRET', '')
SESSION_SECONDS = 12 * 60 * 60
hasher = PasswordHasher()
# Server-side throttling for a single-browser login session. A reverse-proxy
# or provider-level limiter should be added before allowing broader access.
_login_failures: dict[str, tuple[int, float]] = {}


def session_is_valid() -> bool:
    return (
        app.storage.user.get('authenticated') is True
        and float(app.storage.user.get('expires_at', 0)) > time.time()
    )


def clear_login() -> None:
    app.storage.user['authenticated'] = False
    app.storage.user.pop('expires_at', None)

DEFAULT_TEXT = (
    '상단의 [열기] 버튼을 눌러 PC의 텍스트 파일을 불러오세요.\n\n'
    '- 글자 크기와 줄 간격을 자유롭게 조절할 수 있습니다.\n'
    '- 배경색과 글자색을 취향에 맞게 변경하거나 오른쪽 빠른 테마를 이용할 수 있습니다.\n\n'
    '오른쪽 MY ARCHIVE는 DB 연결 후 책 목록이 나타납니다.'
)

ui.add_head_html("""
<style>
html, body, #app { height:100%; margin:0; }\nbody { margin:0; font-family:'Malgun Gothic','Noto Sans KR',sans-serif; background:#edf2f6; }
.q-page { min-height:0!important; height:100dvh!important; overflow:hidden!important; }
.nicegui-content { padding:0!important; margin:0!important; width:100%!important; height:100dvh!important; min-height:0!important; overflow:hidden!important; }
html, body, #app { overflow:hidden!important; }
.reader-shell { display:flex; flex-direction:column; width:100%; height:100dvh; max-height:100dvh; min-height:0; overflow:hidden; background:#edf2f6; }
.reader-header { height:31px; flex:0 0 31px; background:#0877c6; color:white; padding:5px 12px; font-size:12px; }
.reader-toolbar { flex:0 0 auto; display:flex; flex-wrap:wrap; align-items:center; gap:5px; padding:7px 10px; background:#f1f1f1; border-bottom:1px solid #d0d4d8; min-height:54px; }
.reader-toolbar .q-btn.selected-tool { background:#234b70!important; color:#ffffff!important; border-color:#173a5c!important; box-shadow:inset 0 0 0 1px #173a5c!important; }
.reader-toolbar .q-btn { min-height:28px; padding:0 7px; font-size:12px; border:1px solid #bfc4c9; border-radius:1px; background:#fafafa; color:#1e252c; box-shadow:none; text-transform:none; }
.reader-toolbar .q-field { font-size:12px; }
.reader-toolbar .q-field__control { min-height:30px; height:30px; }
.reader-toolbar .q-field__native { min-height:30px; padding:0; }
.reader-content { flex:1 1 0; height:0; display:flex; flex-wrap:nowrap!important; align-items:stretch!important; min-height:0; padding:0 8px 8px; gap:2px; overflow:hidden; }
.reader-main { position:relative; min-width:0; min-height:0; height:100%; flex:1 1 0; background:white; overflow:hidden; }
.reader-pane { position:absolute; inset:0; width:100%; height:100%; min-height:0; }
.reader-pane .q-field__inner, .reader-pane .q-field__control, .reader-pane .q-field__control-container { height:100%; min-height:0; }
.reader-pane .q-field__control { padding:0; }
.reader-pane .q-field__native { height:100%!important; max-height:100%; min-height:0!important; resize:none!important; overflow:auto!important; padding:24px 22px 52px!important; color:var(--read-fg,#1e242b)!important; background:var(--read-bg,#ffffff)!important; font-size:var(--read-size,16px)!important; line-height:var(--read-line,1.85)!important; }
.reader-pane .q-field__control:before,.reader-pane .q-field__control:after { display:none!important; }
.reader-copy { position:absolute; right:14px; bottom:12px; z-index:1; }
.reader-copy .q-btn { font-size:12px; min-height:29px; background:#e4e7ff; color:#283c97; }
.reader-side { flex:0 0 222px; width:222px; min-width:0; min-height:0; height:100%; border-left:2px solid #a4b9c9; background:#eff4f8; display:flex; flex-direction:column; overflow:hidden; }
.reader-side-head { padding:4px 6px; border-bottom:1px solid #bdc9d3; }
.reader-side-head .q-field__control { height:27px; min-height:27px; background:#dbe7f2; }
.reader-side-head .q-field__native { min-height:27px; padding:0 5px; font-size:12px; }
.archive-label { font-size:12px; font-weight:bold; padding:6px 7px 4px; }
.archive-scroller { flex:1; overflow:auto; }
.archive-entry { display:flex; flex-wrap:nowrap; align-items:center; width:100%; min-height:29px; padding:0 2px 0 5px; margin:0; gap:2px; border:1px solid #92b3d0; background:#e5f0f8; transition:background-color .12s ease; }
.archive-entry:hover { background:#82bee9!important; }
.archive-entry.archive-active { background:#b5dafa; border-color:#598db8; }
.archive-entry.archive-active:hover { background:#72b6e7!important; }
.archive-entry .q-btn.archive-title { flex:1 1 0; min-width:0; min-height:26px; padding:0 3px; justify-content:flex-start!important; text-align:left!important; color:#183047!important; font-size:12px; font-weight:400; text-transform:none; }
.archive-entry.archive-active .q-btn.archive-title { font-weight:700; }
.archive-entry .q-btn.archive-delete { flex:0 0 25px; width:25px; min-width:25px; min-height:25px; padding:0; color:#2784c5; }
.archive-entry .q-btn.archive-delete:hover { color:#bd3030; background:rgba(255,255,255,.45); }
.archive-note { margin:5px 8px; padding:12px 7px; border:1px dashed #b2bfcb; font-size:11px; color:#64717f; background:#f8fafc; }
.status-note { flex:0 0 auto; font-size:11px; color:#59616d; padding:0 8px 4px; background:#edf2f6; }
@media(max-width:700px) {
 .reader-shell { min-height:100dvh; height:100dvh; }
 .reader-toolbar { padding:5px; gap:3px; }
 .reader-side { flex-basis:150px; width:150px; }
 .reader-pane .q-field__native { padding:14px 12px 48px!important; }
}
</style>
""", shared=True)


@ui.page('/')
def index():
    if not STORAGE_SECRET or not PASSWORD_HASH:
        with ui.column().classes('items-center mx-auto mt-20 gap-4'):
            ui.label('TXT Reader — 초기 보안 설정 필요').classes('text-xl font-bold')
            ui.label('Render에 APP_PASSWORD_HASH 및 STORAGE_SECRET을 설정하세요.')
            ui.label('인증 설정이 완료되기 전에는 문서 화면을 열 수 없습니다.')
        return

    if not session_is_valid():
        clear_login()
        with ui.column().classes('items-center mx-auto mt-20 gap-4 w-full'):
            with ui.card().classes('w-full max-w-sm p-5 gap-4'):
                ui.label('TXT Reader 로그인').classes('text-xl font-bold')
                password_input = ui.input('숫자 4자리 PIN', password=True, password_toggle_button=True).props('maxlength=4 inputmode=numeric pattern=[0-9]{4}').props('outlined').classes('w-full')
                notice = ui.label('').classes('text-sm text-red-700')

                async def try_login():
                    identifier = ui.context.client.id
                    count, blocked_until = _login_failures.get(identifier, (0, 0.0))
                    if blocked_until > time.monotonic():
                        notice.text = '로그인 시도가 제한되었습니다. 잠시 후 다시 시도하세요.'
                        return
                    try:
                        pin = password_input.value or ''
                        valid = (len(pin) == 4 and pin.isascii() and pin.isdecimal() and
                                 hasher.verify(PASSWORD_HASH, pin))
                    except (argon_errors.VerifyMismatchError, argon_errors.VerificationError, argon_errors.InvalidHashError):
                        valid = False
                    if not valid:
                        count += 1
                        _login_failures[identifier] = (count, time.monotonic() + 300 if count >= 5 else 0.0)
                        password_input.value = ''
                        notice.text = '비밀번호가 올바르지 않습니다.'
                        return
                    _login_failures.pop(identifier, None)
                    app.storage.user['authenticated'] = True
                    app.storage.user['expires_at'] = time.time() + SESSION_SECONDS
                    ui.navigate.to('/')

                ui.button('로그인', on_click=try_login).classes('w-full')
                password_input.on('keydown.enter', try_login)
        return

    state = {'source': 'new', 'editing': False, 'theme': '라이트', 'book_id': None, 'original_name': '', 'original_text': ''}
    themes = {'라이트': ('#ffffff', '#1e242b'), '다크': ('#202124', '#f1f1f1'), '세피아': ('#f5ecd9', '#4b3d2b')}
    colors = {'bg': '#ffffff', 'fg': '#1e242b'}

    def refresh_selected():
        # Keep every button's original blue appearance. Only active text changes.
        active_style = ('background:#569bd5!important;color:#000000!important;'
                        'font-weight:800!important;border:1px solid #bfc4c9!important;'
                        'box-shadow:none!important;')
        idle_style = ('background:#569bd5!important;color:#ffffff!important;'
                      'font-weight:400!important;border:1px solid #bfc4c9!important;'
                      'box-shadow:none!important;')
        for name, button in theme_buttons.items():
            button.style(active_style if name == state['theme'] else idle_style)
        read_button.style(idle_style if state['editing'] else active_style)
        edit_button.style(active_style if state['editing'] else idle_style)

    def set_theme(name):
        state['theme'] = name
        colors['bg'], colors['fg'] = themes[name]
        apply_style()
        refresh_selected()

    def custom_color(kind, value):
        colors[kind] = value
        state['theme'] = None
        apply_style()
        refresh_selected()

    def apply_style():
        size = int(font_size.value or 16)
        space = float(line_spacing.value or 1.8)
        panel.style(
            f'--read-bg:{colors["bg"]};--read-fg:{colors["fg"]};'
            f'--read-size:{size}px;--read-line:{space};'
        )

    def set_mode(edit):
        state['editing'] = edit
        if edit:
            reader.props(remove='readonly')
        else:
            reader.props('readonly')
        mode_label.text = '수정 모드' if edit else '읽기 모드'
        refresh_selected()

    def new_page():
        filename.value = ''
        reader.value = ''
        state.update(source='new', book_id=None, original_name='', original_text='')
        set_mode(True)
        ui.notify('새 페이지를 만들었습니다.')

    def switch_to_read():
        if state['source'] == 'db':
            filename.value = state['original_name']
            reader.value = state['original_text']
        set_mode(False)

    async def load_text(event):
        try:
            raw = event.file.read()
            if inspect.isawaitable(raw):
                raw = await raw
            if len(raw) > MAX_BYTES:
                ui.notify('TXT는 최대 3MB까지 지원합니다.', type='negative')
                return
            try:
                content = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                try:
                    content = raw.decode('cp949')
                except UnicodeDecodeError:
                    ui.notify('UTF-8 또는 CP949 인코딩만 지원합니다.', type='negative')
                    return
            filename.value = event.file.name.rsplit('.', 1)[0]
            reader.value = content
            state.update(source='pc', book_id=None, original_name=filename.value, original_text=content)
            set_mode(False)
            ui.notify(f'TXT 파일을 불러왔습니다: {event.file.name}', type='positive')
        except Exception:
            logging.exception('TXT upload failed')
            ui.notify('파일 읽기에 실패했습니다. Render Logs를 확인해주세요.', type='negative')
        finally:
            uploader.reset()

    def require_login():
        if not session_is_valid():
            ui.notify('세션이 만료되었습니다. 다시 로그인하세요.', type='negative')
            ui.navigate.to('/')
            return False
        return True

    def save_to_db():
        if not require_login():
            return
        try:
            book_id = db.save_book(state['book_id'], filename.value or '', reader.value or '')
            state.update(source='db', book_id=book_id,
                         original_name=filename.value, original_text=reader.value or '')
            set_mode(False)
            reload_books()
            ui.notify('DB 저장 완료', type='positive')
        except Exception:
            logging.exception('DB save failed')
            ui.notify('저장 실패: 파일명, 용량, DB 연결을 확인하세요.', type='negative')

    def open_book(book_id):
        if not require_login():
            return
        try:
            book = db.get_book(book_id)
            if not book:
                ui.notify('문서를 찾을 수 없습니다.', type='warning')
                return
            state.update(source='db', book_id=book[0], original_name=book[1], original_text=book[2])
            filename.value = book[1]
            reader.value = book[2]
            set_mode(False)
            reload_books()
            ui.notify('DB 문서를 불러왔습니다.', type='positive')
        except Exception:
            logging.exception('DB load failed')
            ui.notify('DB 문서를 열지 못했습니다.', type='negative')

    def remove_book(book_id):
        if not require_login():
            return
        try:
            db.delete_book(book_id)
            if state['book_id'] == book_id:
                new_page()
            reload_books()
            ui.notify('영구 삭제했습니다.', type='positive')
        except Exception:
            logging.exception('DB delete failed')
            ui.notify('삭제에 실패했습니다.', type='negative')

    def confirm_delete(book_id, name):
        with ui.dialog() as dialog, ui.card():
            ui.label(f'“{name}” 문서를 영구 삭제할까요?')
            with ui.row():
                ui.button('취소', on_click=dialog.close)
                ui.button('영구 삭제', color='negative',
                          on_click=lambda: (dialog.close(), remove_book(book_id)))
        dialog.open()

    def reload_books():
        if not require_login():
            return
        archive.clear()
        try:
            books = db.list_books()
            with archive:
                for book_id, book_name, modified in books:
                    selected = book_id == state['book_id']
                    with ui.row().classes('archive-entry' + (' archive-active' if selected else '')):
                        ui.button(book_name, on_click=lambda bid=book_id: open_book(bid)).props('flat no-caps dense').classes('archive-title').tooltip(book_name)
                        ui.button(icon='delete_outline', on_click=lambda bid=book_id, name=book_name: confirm_delete(bid, name)).props('flat round dense').classes('archive-delete').tooltip('삭제')
                if not books:
                    ui.label('저장된 책이 없습니다.').classes('text-xs p-2')
        except Exception:
            logging.exception('DB listing failed')
            with archive:
                ui.label('DB 연결이 필요합니다. Render DATABASE_URL을 확인하세요.').classes('text-xs p-2 text-red-600')

    def logout():
        clear_login()
        ui.navigate.to('/')

    with ui.column().classes('reader-shell w-full gap-0'):
        ui.label('텍스트 북리더').classes('reader-header w-full')
        with ui.row().classes('reader-toolbar w-full'):
            uploader = ui.upload(
                on_upload=load_text,
                on_rejected=lambda: ui.notify('TXT 파일은 최대 3MB입니다.', type='negative'),
                auto_upload=True,
                max_file_size=MAX_BYTES,
            ).props('accept=.txt').classes('hidden')
            open_button = ui.button('📂 열기')
            open_button.on(
                'click',
                js_handler=f'() => getElement({uploader.id}).$refs.qRef.pickFiles()',
            )
            ui.button('새 페이지', on_click=new_page)
            ui.label('글크기:')
            font_size = ui.number(value=16, min=10, max=36, step=1).props('dense outlined').classes('w-16')
            ui.label('줄간격:')
            line_spacing = ui.number(value=1.8, min=1.0, max=3.0, step=0.1, format='%.1f').props('dense outlined').classes('w-16')
            with ui.dialog() as background_dialog, ui.card():
                ui.label('바탕색 변경')
                ui.color_input(label='배경색', value='#ffffff',
                               on_change=lambda e: custom_color('bg', e.value))
                ui.button('닫기', on_click=background_dialog.close)
            ui.button('바탕색 변경', on_click=background_dialog.open)
            with ui.dialog() as foreground_dialog, ui.card():
                ui.label('글자색 변경')
                ui.color_input(label='글자색', value='#1e242b',
                               on_change=lambda e: custom_color('fg', e.value))
                ui.button('닫기', on_click=foreground_dialog.close)
            ui.button('글자색 변경', on_click=foreground_dialog.open)
            ui.separator().props('vertical').classes('h-6 mx-1')
            theme_buttons = {
                label: ui.button(label, on_click=lambda name=label: set_theme(name))
                for label in themes
            }
            ui.separator().props('vertical').classes('h-6 mx-1')
            read_button = ui.button('읽기', on_click=switch_to_read)
            edit_button = ui.button('수정', on_click=lambda: set_mode(True))
            ui.space()
            ui.button('DB 저장하기', on_click=save_to_db)
            ui.button('로그아웃', on_click=logout)
        with ui.row().classes('reader-content w-full gap-0'):
            with ui.column().classes('reader-main gap-0') as panel:
                reader = ui.textarea(value=DEFAULT_TEXT).props('borderless readonly').classes('reader-pane w-full')
                with ui.row().classes('reader-copy'):
                    ui.button('복사', on_click=lambda: ui.run_javascript(
                        f'navigator.clipboard.writeText({json.dumps(reader.value or "", ensure_ascii=False)})'
                    ))
            with ui.column().classes('reader-side gap-0'):
                with ui.row().classes('reader-side-head w-full items-center gap-1'):
                    ui.label('File Name').classes('text-xs font-bold')
                    filename = ui.input().props('dense borderless').classes('grow min-w-0')
                ui.label('MY ARCHIVE').classes('archive-label')
                with ui.column().classes('archive-scroller w-full gap-0') as archive:
                    ui.label('DB 연결 후 목록 새로고침').classes('archive-note')
        with ui.row().classes('status-note w-full items-center gap-3'):
            mode_label = ui.label('읽기 모드')
            ui.label('NeonDB 연결 · 개인 서재')

    font_size.on('update:model-value', apply_style)
    line_spacing.on('update:model-value', apply_style)
    apply_style()
    refresh_selected()
    if os.getenv('DATABASE_URL'):
        try:
            db.ensure_schema()
            reload_books()
        except Exception:
            logging.exception('Neon initialization failed')


ui.run(
    host='0.0.0.0',
    port=int(os.getenv('PORT', '8080')),
    reload=False,
    title='TXT Reader',
    storage_secret=STORAGE_SECRET or 'NOT_CONFIGURED__DO_NOT_USE_FOR_PRODUCTION',
)
