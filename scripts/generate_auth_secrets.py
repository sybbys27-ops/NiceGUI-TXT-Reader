"""Run locally: python scripts/generate_auth_secrets.py

Never copy plaintext passwords into source code or commit output to GitHub.
"""
import getpass
import secrets
from argon2 import PasswordHasher

password = getpass.getpass('새 숫자 4자리 PIN: ')
confirmation = getpass.getpass('PIN 확인: ')
if password != confirmation or len(password) != 4 or not password.isascii() or not password.isdecimal():
    raise SystemExit('PIN이 일치하지 않거나 숫자 4자리가 아닙니다.')
print('\nRender Environment에 다음 값을 각각 등록하세요:')
print('APP_PASSWORD_HASH=' + PasswordHasher().hash(password))
print('STORAGE_SECRET=' + secrets.token_urlsafe(48))
print('\n이 출력값을 GitHub에 저장하지 마세요.')
