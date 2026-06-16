[app]

title = AI Yordamchi

package.name = aiyordamchi

package.domain = org.xudoyberdi

source.dir = .

source.include_exts = py,png,jpg,kv,atlas,json,txt

version = 1.0

requirements = python3,kivy,requests,telethon,qrcode,pillow,certifi,pyaes,rsa

orientation = portrait

fullscreen = 0

android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

android.api = 34

android.minapi = 23

android.ndk = 25b

android.archs = arm64-v8a, armeabi-v7a

android.accept_sdk_license = True

presplash.color = #FFFFFF

icon.filename = icon.png

[buildozer]

log_level = 2

warn_on_root = 0
