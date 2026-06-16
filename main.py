import asyncio
import json
import os
import re
import threading
from io import BytesIO

from kivy.app import App
from kivy.clock import Clock
from kivy.core.image import Image as CoreImage
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


GROQ_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
API_ID = int(os.getenv("TG_API_ID", "30774238"))
API_HASH = os.getenv("TG_API_HASH", "e7ff0947b5f979b672e94c8e35ba1402")

# Regex naqshlarini dastur boshida kompilyatsiya qilish (Tezlik uchun)
RE_DELAY = re.compile(r"\s+(\d+)\s*(sekund|soniya|minut|daqiqa)(dan)?\s+keyin\s*$", re.IGNORECASE)
RE_BULK = re.compile(r"\b(hamma|barcha)\s+(kontakt|kontaktlar|kontaktlarga)\b", re.IGNORECASE)
RE_USERNAME = re.compile(r"^(@[A-Za-z0-9_]{5,32})\s+(.+)$")
RE_DEB_YOZ = re.compile(r"\s+deb\s+(yoz|yubor|jonat|jo'nat)$", re.IGNORECASE)
RE_YOZ = re.compile(r"\s+(yoz|yubor|jonat|jo'nat)$", re.IGNORECASE)
RE_PATTERNS = [
    re.compile(r"^(.+?)\s+ga\s+(.+?)\s+deb\s+(yoz|yubor|jonat|jo'nat)$", re.IGNORECASE),
    re.compile(r"^(.+?)ga\s+(.+?)\s+deb\s+(yoz|yubor|jonat|jo'nat)$", re.IGNORECASE),
    re.compile(r"^(.+?)\s+ga\s+(.+?)\s+(yoz|yubor|jonat|jo'nat)$", re.IGNORECASE),
    re.compile(r"^(.+?)ga\s+(.+?)\s+(yoz|yubor|jonat|jo'nat)$", re.IGNORECASE),
]

try:
    import requests
except Exception:
    requests = None

try:
    import qrcode
except Exception:
    qrcode = None

try:
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    from telethon.tl.functions.contacts import GetContactsRequest
except Exception:
    TelegramClient = None
    SessionPasswordNeededError = Exception
    GetContactsRequest = None


class Bubble(Label):
    def __init__(self, text, is_user=False, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.markup = True
        self.size_hint_y = None
        self.halign = "left"
        self.valign = "top"
        self.padding = (dp(12), dp(10))
        self.text_size = (0, None)
        self.color = (0.92, 0.94, 1, 1)
        self.bind(width=self._resize, texture_size=self._texture)
        with self.canvas.before:
            Color(*(0.16, 0.16, 0.28, 1) if is_user else (0.08, 0.20, 0.16, 1))
            self.bg = RoundedRectangle(radius=[dp(10)])
        self.bind(pos=self._draw, size=self._draw)

    def _resize(self, *_):
        self.text_size = (self.width - dp(24), None)

    def _texture(self, *_):
        self.height = self.texture_size[1] + dp(20)

    def _draw(self, *_):
        self.bg.pos = self.pos
        self.bg.size = self.size


class AndroidAIApp(App):
    def build(self):
        self.title = "AI Yordamchi"
        self.tg_client = None
        self.tg_loop = None
        self.tg_me = None
        self.chat_history = []
        self.groq_key = GROQ_KEY
        self.load_settings()

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        header = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        title = Label(text="[b]AI Yordamchi[/b]", markup=True, font_size=dp(22), halign="left")
        title.bind(size=lambda obj, *_: setattr(obj, "text_size", obj.size))
        key_button = Button(text="Groq", size_hint_x=None, width=dp(78))
        key_button.bind(on_press=lambda *_: self.open_groq_popup())
        self.tg_button = Button(text="TG ulash", size_hint_x=None, width=dp(110))
        self.tg_button.bind(on_press=lambda *_: self.connect_telegram())
        header.add_widget(title)
        header.add_widget(key_button)
        header.add_widget(self.tg_button)
        root.add_widget(header)

        self.chat_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(8))
        self.chat_box.bind(minimum_height=self.chat_box.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.chat_box)
        root.add_widget(scroll)
        self.scroll = scroll

        input_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(8))
        self.input = TextInput(
            hint_text="@username salom deb yoz",
            multiline=False,
            font_size=dp(16),
        )
        send = Button(text="Yubor", size_hint_x=None, width=dp(92))
        send.bind(on_press=lambda *_: self.send_input())
        input_row.add_widget(self.input)
        input_row.add_widget(send)
        root.add_widget(input_row)

        Clock.schedule_once(lambda *_: self.add_bot(
            "Assalomu alaykum! Telegram uchun avval TG ulash tugmasini bosing.\n"
            "Misol: @username salom aka deb yoz"
        ), 0.2)
        return root

    def add_message(self, text, is_user=False):
        prefix = "[b]Siz:[/b]\n" if is_user else "[b]Bot:[/b]\n"
        bubble = Bubble(prefix + text, is_user=is_user)
        self.chat_box.add_widget(bubble)
        Clock.schedule_once(lambda *_: setattr(self.scroll, "scroll_y", 0), 0.05)

    def add_bot(self, text):
        self.add_message(text, False)

    @property
    def settings_path(self):
        return os.path.join(self.user_data_dir, "settings.json")

    def load_settings(self):
        try:
            if not os.path.exists(self.settings_path):
                return
            with open(self.settings_path, "r", encoding="utf-8") as file:
                data = json.load(file)
            key = (data.get("groq_key") or "").strip()
            if key:
                self.groq_key = key
        except Exception:
            pass

    def save_settings(self):
        os.makedirs(self.user_data_dir, exist_ok=True)
        with open(self.settings_path, "w", encoding="utf-8") as file:
            json.dump({"groq_key": self.groq_key}, file)

    def open_groq_popup(self):
        box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
        entry = TextInput(
            text=self.groq_key,
            hint_text="gsk_...",
            multiline=False,
            password=True,
            font_size=dp(15),
        )
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        cancel = Button(text="Bekor")
        save = Button(text="Saqlash")
        buttons.add_widget(cancel)
        buttons.add_widget(save)
        box.add_widget(Label(text="Groq API kalit", size_hint_y=None, height=dp(32)))
        box.add_widget(entry)
        box.add_widget(buttons)
        popup = Popup(title="Sozlama", content=box, size_hint=(0.9, 0.36))
        cancel.bind(on_press=lambda *_: popup.dismiss())
        save.bind(on_press=lambda *_: self.set_groq_key(entry.text, popup))
        popup.open()

    def set_groq_key(self, key, popup):
        key = key.strip()
        if not key:
            self.add_bot("Groq kalit bo'sh bo'lmasin.")
            return
        if not requests:
            self.add_bot("Requests kutubxonasi APK ichida topilmadi.")
            return
        try:
            self.groq_key = key
            self.save_settings()
            popup.dismiss()
            self.add_bot("Groq kalit saqlandi.")
        except Exception as exc:
            self.add_bot(f"Groq kalit saqlanmadi: {exc}")

    def send_input(self):
        text = self.input.text.strip()
        if not text:
            return
        self.input.text = ""
        self.add_message(text, True)
        threading.Thread(target=self.handle_text, args=(text,), daemon=True).start()

    def handle_text(self, text):
        result = self.process_text(text)
        Clock.schedule_once(lambda *_: self.add_bot(result), 0)

    def process_text(self, text):
        command = self.parse_telegram_command(text)
        if command:
            if command == "BULK_BLOCKED":
                return "Hamma kontaktlarga avtomatik yuborilmaydi. Kontakt yoki username aniq yozilsin."
            names, message, delay = command
            return self.telegram_send(names, message, delay)
        return self.ai_answer(text)

    def ai_answer(self, text):
        if not self.groq_key:
            return "Groq API kalit topilmadi. APK uchun GROQ_API_KEY sozlanishi kerak."
        if not requests:
            return "Requests kutubxonasi topilmadi."
        try:
            self.chat_history.append({"role": "user", "content": text})
            messages = [
                {
                    "role": "system",
                    "content": "Sen ozbek tilida qisqa va dostona javob beradigan yordamchisan.",
                }
            ] + self.chat_history[-10:]
            
            headers = {
                "Authorization": f"Bearer {self.groq_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 700
            }
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            answer = response.json()["choices"][0]["message"]["content"]
            self.chat_history.append({"role": "assistant", "content": answer})
            return answer
        except Exception as exc:
            return f"Groq xatolik: {exc}"

    def parse_telegram_command(self, text):
        cleaned = re.sub(r"^\s*telegram(dan|da)?\s+", "", text.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned)
        delay = 0

        delay_match = RE_DELAY.search(cleaned)
        if delay_match:
            value = int(delay_match.group(1))
            unit = delay_match.group(2).lower()
            delay = value * 60 if unit in ("minut", "daqiqa") else value
            cleaned = cleaned[: delay_match.start()].strip()

        if RE_BULK.search(cleaned):
            return "BULK_BLOCKED"

        username_match = RE_USERNAME.search(cleaned)
        if username_match:
            username = username_match.group(1)
            message = username_match.group(2).strip()
            message = RE_DEB_YOZ.sub("", message).strip()
            message = RE_YOZ.sub("", message).strip()
            return ([username], message, delay) if message else None

        for pattern in RE_PATTERNS:
            match = pattern.search(cleaned)
            if not match:
                continue
            names = [n.strip(" ,") for n in re.split(r"\s*,\s*|\s+va\s+", match.group(1)) if n.strip(" ,")]
            message = match.group(2).strip()
            if names and message:
                return names, message, delay
        return None

    def connect_telegram(self):
        if not TelegramClient:
            self.add_bot("Telethon o'rnatilmagan.")
            return
        self.tg_button.disabled = True
        self.tg_button.text = "Ulanmoqda"
        threading.Thread(target=self._telegram_thread, daemon=True).start()

    def _telegram_thread(self):
        self.tg_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.tg_loop)
        self.tg_client = TelegramClient("tg_session_android", API_ID, API_HASH, loop=self.tg_loop)
        self.tg_loop.run_until_complete(self._telegram_connect_async())

    async def _telegram_connect_async(self):
        try:
            await self.tg_client.connect()
            if not await self.tg_client.is_user_authorized():
                qr_login = await self.tg_client.qr_login()
                Clock.schedule_once(lambda *_: self.show_qr(qr_login.url), 0)
                try:
                    await qr_login.wait(timeout=90)
                except SessionPasswordNeededError:
                    Clock.schedule_once(lambda *_: self.add_bot("2FA parol kerak. Bu APK versiyada hozircha QR 2FA oynasi yo'q."), 0)
                    return
                except asyncio.TimeoutError:
                    Clock.schedule_once(lambda *_: self.add_bot("QR vaqti tugadi. Qayta TG ulash bosing."), 0)
                    return

            self.tg_me = await self.tg_client.get_me()
            name = self.telegram_name(self.tg_me)
            Clock.schedule_once(lambda *_: self.add_bot(f"Telegram {name} nomidan ulandi."), 0)
            Clock.schedule_once(lambda *_: self._tg_connected_ui(), 0)
            await self.tg_client.run_until_disconnected()
        except Exception as exc:
            Clock.schedule_once(lambda *_: self.add_bot(f"Telegram xatolik: {exc}"), 0)
            Clock.schedule_once(lambda *_: self._tg_disconnected_ui(), 0)

    def _tg_connected_ui(self):
        self.tg_button.disabled = False
        self.tg_button.text = "TG ulandi"

    def _tg_disconnected_ui(self):
        self.tg_button.disabled = False
        self.tg_button.text = "TG ulash"

    def show_qr(self, url):
        if not qrcode:
            self.add_bot("qrcode kutubxonasi topilmadi.")
            return
        image = qrcode.make(url).resize((512, 512))
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        texture = CoreImage(buffer, ext="png").texture
        qr_image = Image(texture=texture, size_hint=(1, 1))
        popup = Popup(title="Telegram QR", content=qr_image, size_hint=(0.88, 0.62))
        popup.open()

    def telegram_name(self, user):
        if not user:
            return "ulangan akkaunt"
        full_name = " ".join(filter(None, [getattr(user, "first_name", None), getattr(user, "last_name", None)])).strip()
        if full_name:
            return full_name
        username = getattr(user, "username", None)
        return f"@{username}" if username else str(getattr(user, "id", "ulangan akkaunt"))

    async def find_telegram_user(self, contacts, name):
        if name.startswith("@"):
            try:
                return await self.tg_client.get_entity(name), None
            except Exception:
                pass

        query = name.lower().strip()
        exact = []
        partial = []
        for user in contacts.users:
            first = (user.first_name or "").strip()
            last = (user.last_name or "").strip()
            username = (user.username or "").strip()
            variants = [first, last, f"{first} {last}".strip(), username, f"@{username}" if username else ""]
            variants = [v.lower() for v in variants if v]
            if query in variants:
                exact.append(user)
            elif any(query in v for v in variants):
                partial.append(user)

        if len(exact) == 1:
            return exact[0], None
        if len(exact) > 1:
            return None, exact
        if len(partial) == 1:
            return partial[0], None
        if len(partial) > 1:
            return None, partial

        username = name if name.startswith("@") else f"@{name}"
        if re.fullmatch(r"@[A-Za-z0-9_]{5,32}", username):
            try:
                return await self.tg_client.get_entity(username), None
            except Exception:
                pass
        return None, None

    def telegram_send(self, names, message, delay=0):
        if not self.tg_client or not self.tg_client.is_connected():
            return "Telegram ulanmagan. Avval TG ulash tugmasini bosing."
        if len(names) > 5:
            return "Bir buyruqda ko'pi bilan 5 ta kontaktga yuboriladi."

        async def prepare_task():
            contacts = await self.tg_client(GetContactsRequest(hash=0))
            valid_users = []
            results = []
            for name in names:
                user, matches = await self.find_telegram_user(contacts, name)
                if matches:
                    options = ", ".join(self.telegram_name(u) for u in matches[:5])
                    results.append(f"{name}: bir nechta mos kontakt topildi: {options}")
                    continue
                if not user:
                    results.append(f"{name}: topilmadi")
                    continue
                valid_users.append((user, name))

            return valid_users, results

        async def delay_send_task(valid_users, msg):
            await asyncio.sleep(delay)
            for user, name in valid_users:
                try:
                    await self.tg_client.send_message(user, msg)
                except Exception as e:
                    print(f"Xatolik: {e}")

        # Fetch users asynchronously but wait for it
        future_prepare = asyncio.run_coroutine_threadsafe(prepare_task(), self.tg_loop)
        try:
            valid_users, results = future_prepare.result(timeout=15)
        except Exception as exc:
            return f"Kontaktni izlashda xatolik: {exc}"

        if not valid_users:
            return "\n".join(results)

        # Users found, schedule sending asynchronously
        if delay > 0:
            asyncio.run_coroutine_threadsafe(delay_send_task(valid_users, message), self.tg_loop)
            for user, name in valid_users:
                results.append(f"{self.telegram_name(user)} ga {delay} sekunddan keyin yuboriladi.")
        else:
            # Send immediately
            async def send_now_task():
                for user, name in valid_users:
                    try:
                        await self.tg_client.send_message(user, message)
                        results.append(f"{self.telegram_name(user)} ga yuborildi: {message}")
                    except Exception as e:
                        results.append(f"{name}: xatolik {e}")
            
            future_send = asyncio.run_coroutine_threadsafe(send_now_task(), self.tg_loop)
            try:
                future_send.result(timeout=15)
            except Exception as exc:
                return f"Yuborishda xatolik: {exc}"

        return "\n".join(results)

if __name__ == "__main__":
    AndroidAIApp().run()
