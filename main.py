"""NiceGUI TXT Reader — initial UI prototype (no database or authentication yet)."""
import json
import os
from nicegui import ui

MAX_BYTES = 3 * 1024 * 1024

ui.add_head_html("""
<style>
body { font-family: 'Malgun Gothic', 'Noto Sans KR', sans-serif; }
.reader textarea { line-height: 1.85 !important; }
</style>
""")

@ui.page('/')
def index():
    saved_name = ''
    saved_text = ''
    editing = False

    with ui.column().classes('w-full max-w-6xl mx-auto p-4 gap-3'):
        ui.label('TXT Reader').classes('text-2xl font-bold')
        ui.label('NiceGUI 학습용 초기 화면 · 아직 DB 저장/로그인이 연결되지 않았습니다.').classes('text-sm text-orange-700')
        with ui.row().classes('w-full items-center gap-3 flex-wrap'):
            filename = ui.input('File Name', placeholder='책 이름 입력').classes('grow min-w-60')
            font_size = ui.number('글자 크기', value=18, min=12, max=36, step=1).classes('w-28')
            theme = ui.select(['밝게', '세피아', '어둡게'], value='밝게', label='배경').classes('w-32')
        reader = ui.textarea(placeholder='새 페이지에 TXT 내용을 붙여넣으세요.').props('outlined readonly').classes('w-full reader')
        reader.style('min-height: 65vh;')
        status = ui.label('새 문서').classes('text-sm text-gray-600')

        def update_style():
            colors = {'밝게': ('#ffffff', '#202020'), '세피아': ('#f6ecd7', '#493b2b'), '어둡게': ('#202124', '#eeeeee')}
            bg, fg = colors[theme.value]
            reader.style(f'min-height:65vh; font-size:{int(font_size.value or 18)}px; background:{bg}; color:{fg};')

        def set_mode(value: bool):
            nonlocal editing
            editing = value
            reader.props(remove='readonly' if value else None, add='readonly' if not value else None)
            status.text = '수정 모드 (DB 미연결)' if value else '읽기 모드'

        def new_document():
            nonlocal saved_name, saved_text
            saved_name = ''
            saved_text = ''
            filename.value = ''
            reader.value = ''
            set_mode(True)
            status.text = '새 문서 · 아직 저장되지 않음'

        def read_mode():
            # DB-loaded documents will revert to the last saved version in a later milestone.
            # For unsaved PC/new documents, preserve current edits to prevent data loss.
            set_mode(False)

        async def load_txt(event):
            nonlocal saved_name, saved_text
            raw = event.content.read()
            if len(raw) > MAX_BYTES:
                ui.notify('TXT 최대 크기는 3MB입니다.', type='negative')
                return
            try:
                data = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                try:
                    data = raw.decode('cp949')
                except UnicodeDecodeError:
                    ui.notify('UTF-8 또는 CP949 TXT만 지원합니다.', type='negative')
                    return
            saved_name = event.name.rsplit('.', 1)[0]
            saved_text = data
            filename.value = saved_name
            reader.value = data
            set_mode(False)
            status.text = 'PC에서 읽음 · DB에 저장되지 않음'

        with ui.row().classes('items-center flex-wrap gap-2'):
            ui.button('새 페이지', on_click=new_document, icon='note_add')
            ui.upload(label='PC TXT 불러오기', on_upload=load_txt, auto_upload=True, max_file_size=MAX_BYTES).props('accept=.txt').classes('max-w-xs')
            ui.button('읽기', on_click=read_mode, icon='menu_book')
            ui.button('수정', on_click=lambda: set_mode(True), icon='edit')
            ui.button('전체 복사', icon='content_copy', on_click=lambda: ui.run_javascript(
                f'navigator.clipboard.writeText({json.dumps(reader.value or "")})'
            ))
            ui.button('DB 저장하기 (다음 단계)', on_click=lambda: None).props('disable')
            ui.button('DB 불러오기 (다음 단계)', on_click=lambda: None).props('disable')
        font_size.on('update:model-value', update_style)
        theme.on('update:model-value', update_style)
        update_style()

ui.run(host='0.0.0.0', port=int(os.getenv('PORT', '8080')), reload=False, title='TXT Reader')
