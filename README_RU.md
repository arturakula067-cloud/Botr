# Lua Deobfuscator Discord Bot

## Что работает
- `/deobfuscate` — загрузка Lua/Luau/TXT, меню выбора, статус и файл результата.
- `/detect` — эвристический поиск сигнатур.
- `/engines` — список модулей и статусы.
- `/ping` — проверка бота.
- Реальный интегрированный модуль: **Prometheus через yennylol/unprom**.
- Остальные пункты меню пока честно сообщают, что декодер не подключён. Это не фальшивая поддержка.

`unprom` — отдельный open-source static parser/deobfuscator. Его README описывает поддержку разных преобразований Prometheus, включая best-effort VM lifting; не гарантирует успех на каждом варианте. Репозиторий и MIT license: https://github.com/yennylol/unprom

Бот не исполняет загруженный Lua-код. Используй только файлы, которые имеешь право анализировать.

## Discord setup
1. https://discord.com/developers/applications → New Application.
2. Bot → Add Bot / Reset Token → скопируй токен, держи его в секрете.
3. OAuth2 → URL Generator: scopes `bot`, `applications.commands`.
4. Permissions: View Channels, Send Messages, Embed Links, Attach Files, Use Application Commands.
5. Открой invite URL и добавь бота на свой сервер.
6. Discord → User Settings → Advanced → Developer Mode. Скопируй ID сервера.

## Локальный запуск Windows
Установи Python 3.11+. Распакуй архив, открой CMD в папке проекта:
```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
```
Скопируй `.env.example` в `.env`, заполни `DISCORD_TOKEN` и `GUILD_ID`, затем:
```bat
py bot.py
```
Проверь `/ping`, `/engines`, `/deobfuscate`.

## Render 24/7
1. Загрузи папку проекта в новый GitHub-репозиторий. Не загружай `.env`.
2. Render → New → Blueprint → выбери репозиторий с `render.yaml`.
3. Убедись, что создаётся Background Worker. Проверь цену плана до подтверждения.
4. В Environment добавь `DISCORD_TOKEN`, `GUILD_ID`; `LOG_CHANNEL_ID` необязателен.
5. Deploy. В логах ищи `Online as ...`.

Создай приватный Discord-канал `admin-logs`, выдай доступ только администраторам и боту, включи Developer Mode, скопируй ID канала в `LOG_CHANNEL_ID`.

## Важно
Render Background Worker — постоянно работающий процесс; Static Site для Discord Gateway-бота не подходит. Не исполняй загруженные файлы через exec/eval/loadstring/shell. Для будущих декодеров используй sandbox с лимитами CPU, памяти и времени. Ознакомься с лицензиями каждого подключаемого проекта.
