"""Desktop-style NiceGUI TXT reader prototype. DB/login are not enabled yet."""
import json
import os

from nicegui import ui

MAX_BYTES = 3 * 1024 * 1024
DEFAULT_TEXT = (
    '상단의 [열기] 버튼을 눌러 PC의 텍스트 파일을 불러오세요.\n\n'
    '- 글자 크기와 줄 간격을 자유롭게 조절할 수 있습니다.\n'
    '- 배경색과 글자색을 취향에 맞게 변경하거나 오른쪽 빠른 테마를 이용할 수 있습니다.\n\n'
    '오른쪽 MY ARCHIVE는 DB 연결 후 책 목록이 나타납니다.'
)

ui.add_head_html("""
<style>
html, body, #app { height:100%; margin:0; }\nbody { margin:0; font-family:'Malgun Gothic','Noto Sans KR',sans-serif; background:#edf2f6; }
.q-page { min-height:100vh; }
.reader-shell { display:flex; flex-direction:column; height:100dvh; min-height:0; overflow:hidden; background:#edf2f6; }
.reader-header { height:31px; flex:0 0 31px; background:#0877c6; color:white; padding:5px 12px; font-size:12px; }
.reader-toolbar { display:flex; flex-wrap:wrap; align-items:center; gap:5px; padding:7px 10px; background:#f1f1f1; border-bottom:1px solid #d0d4d8; min-height:54px; }
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
.archive-note { margin:5px 8px; padding:12px 7px; border:1px dashed #b2bfcb; font-size:11px; color:#64717f; background:#f8fafc; }
.status-note { font-size:11px; color:#59616d; padding:0 8px 4px; background:#edf2f6; }
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
    state = {'source': 'new', 'editing': False}
    themes = {'라이트': ('#ffffff', '#1e242b'), '다크': ('#202124', '#f1f1f1'), '세피아': ('#f5ecd9', '#4b3d2b')}
    colors = {'bg': '#ffffff', 'fg': '#1e242b'}

    def set_theme(name):
        colors['bg'], colors['fg'] = themes[name]
        apply_style()

    def apply_style():
        size = int(font_size.value or 16)
        space = float(line_spacing.value or 1.8)
        panel.style(
            f'--read-bg:{colors["bg"]};--read-fg:{colors["fg"]};'
            f'--read-size:{size}px;--read-line:{space};'
        )

    def set_mode(edit):
        state['editing'] = edit
        reader.props(remove='readonly' if edit else None, add='readonly' if not edit else None)
        mode_label.text = '수정 모드' if edit else '읽기 모드'

    def new_page():
        filename.value = ''
        reader.value = ''
        state['source'] = 'new'
        set_mode(True)
        ui.notify('새 페이지를 만들었습니다.')

    def switch_to_read():
        # DB-loaded unsaved edits will revert when DB persistence is implemented.
        # New or PC-loaded documents must not be silently destroyed.
        set_mode(False)

    async def load_text(event):
        raw = event.content.read()
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
        filename.value = event.name.rsplit('.', 1)[0]
        reader.value = content
        state['source'] = 'pc'
        set_mode(False)
        upload_dialog.close()
        ui.notify('TXT 파일을 불러왔습니다.')

    with ui.column().classes('reader-shell w-full gap-0'):
        ui.label('텍스트 북리더').classes('reader-header w-full')
        with ui.row().classes('reader-toolbar w-full'):
            with ui.dialog() as upload_dialog, ui.card():
                ui.label('PC에서 TXT 파일 열기').classes('font-bold')
                ui.upload(on_upload=load_text, auto_upload=True, max_file_size=MAX_BYTES).props('accept=.txt')
                ui.button('닫기', on_click=upload_dialog.close)
            ui.button('📂 열기', on_click=upload_dialog.open)
            ui.button('새 페이지', on_click=new_page)
            ui.label('글크기:')
            font_size = ui.number(value=16, min=10, max=36, step=1).props('dense outlined').classes('w-16')
            ui.label('줄간격:')
            line_spacing = ui.number(value=1.8, min=1.0, max=3.0, step=0.1, format='%.1f').props('dense outlined').classes('w-16')
            with ui.menu() as background_menu:
                ui.color_input(label='배경색', value='#ffffff', on_change=lambda e: (colors.__setitem__('bg', e.value), apply_style()))
            ui.button('바탕색 변경', on_click=background_menu.open)
            with ui.menu() as foreground_menu:
                ui.color_input(label='글자색', value='#1e242b', on_change=lambda e: (colors.__setitem__('fg', e.value), apply_style()))
            ui.button('글자색 변경', on_click=foreground_menu.open)
            ui.separator().props('vertical').classes('h-6 mx-1')
            for label in themes:
                ui.button(label, on_click=lambda name=label: set_theme(name))
            ui.separator().props('vertical').classes('h-6 mx-1')
            ui.button('읽기', on_click=switch_to_read)
            ui.button('수정', on_click=lambda: set_mode(True))
            ui.space()
            ui.button('DB 불러오기').props('disable').tooltip('NeonDB 연결 후 활성화됩니다.')
            ui.button('DB 저장하기').props('disable').tooltip('NeonDB 연결 후 활성화됩니다.')
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
                with ui.column().classes('archive-scroller w-full gap-0'):
                    ui.label('저장된 책 목록은 NeonDB 연결 후 표시됩니다.').classes('archive-note')
        with ui.row().classes('status-note w-full items-center gap-3'):
            mode_label = ui.label('읽기 모드')
            ui.label('UI 미리보기 · DB 및 인증 미연결 · 개인 문서 업로드 주의')

    font_size.on('update:model-value', apply_style)
    line_spacing.on('update:model-value', apply_style)
    apply_style()


ui.run(host='0.0.0.0', port=int(os.getenv('PORT', '8080')), reload=False, title='TXT Reader')
