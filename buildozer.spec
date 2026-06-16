[app]
title = AI Yordamchi
package.name = aiyordamchi
package.domain = org.user

source.dir = .
source.include_exts = py,png,jpg,kv,atlas
source.exclude_dirs = __pycache__,.git
source.exclude_exts = pyc

version = 0.1

requirements = python3,kivy,requests,telethon,qrcode,pillow,certifi,pyaes,rsa

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,ACCESS_NETWORK_STATE
android.api = 35
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

android.allow_backup = False
android.private_storage = True

[buildozer]
log_level = 2
warn_on_root = 0
