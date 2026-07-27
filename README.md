# Selectel Market — Telegram Bot

Маркетплейс аккаунтов Selectel с автоматической выдачей и оплатой через RollyPay (СБП).

## Требования

- Ubuntu 24.04
- Python 3.11+
- Токен Telegram-бота (BotFather → создать бота)
- API-ключ RollyPay (`api_key` + `signing_secret`)
- Публичный домен/IP для приёма вебхуков RollyPay (опционально, но рекомендуется)

---

## Установка на Ubuntu 24.04

### 1. Скопировать файлы на сервер

```bash
scp -r C:\marketselec ubuntu@YOUR_SERVER_IP:/opt/selectel-market
```

Или клонируйте репозиторий, если используете git.

### 2. Установить зависимости

```bash
cd /opt/selectel-market
sudo apt update && sudo apt install -y python3.11 python3.11-venv python3-pip
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Настроить переменные окружения

```bash
cp .env.example .env
nano .env
```

Заполните:

```ini
BOT_TOKEN=your_bot_token
ADMIN_IDS=123456789          # Telegram ID администраторов через запятую
ROLLYPAY_API_KEY=rpk_live_...
ROLLYPAY_SIGNING_SECRET=...
PUBLIC_WEBHOOK_URL=https://yourdomain.com/webhooks/rollypay
WEBHOOK_PORT=8080
SUPPORT_USERNAME=@your_support
```

### 4. Настроить systemd

```bash
sudo cp selectel-market.service /etc/systemd/system/
# Если пользователь не ubuntu, замените User= в файле сервиса
sudo systemctl daemon-reload
sudo systemctl enable selectel-market
sudo systemctl start selectel-market
```

Проверить статус:
```bash
sudo systemctl status selectel-market
sudo journalctl -u selectel-market -f
```

### 5. Настроить Nginx (reverse proxy для вебхуков)

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    # SSL настройки (certbot / Let's Encrypt)
    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    location /webhooks/rollypay {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 30s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8080;
    }
}
```

Получить SSL-сертификат:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### 6. Указать callback_url в RollyPay

Установить `callback_url` кассы через API:

```bash
curl -X PUT https://rollypay.io/api/v1/terminals/YOUR_TERMINAL_ID \
  -H "X-API-Key: rpk_live_..." \
  -H "X-Nonce: $(uuidgen)" \
  -H "Content-Type: application/json" \
  -d '{"callback_url": "https://yourdomain.com/webhooks/rollypay"}'
```

---

## Структура проекта

```
marketselec/
├── main.py                 # Точка входа
├── config.py               # Конфигурация из .env
├── database.py             # SQLite (aiosqlite)
├── keyboards.py            # Inline / Reply клавиатуры
├── webhook_server.py       # aiohttp-сервер для RollyPay колбэков
├── handlers/
│   ├── start.py            # /start, TOS, главное меню
│   ├── profile.py          # Профиль, история покупок
│   ├── catalog.py          # Каталог и покупка аккаунтов
│   ├── topup.py            # Пополнение баланса (RollyPay)
│   ├── support.py          # Поддержка
│   └── admin.py            # Панель администратора
├── middlewares/
│   └── register.py         # Авторегистрация пользователей
├── utils/
│   └── rollypay.py         # HTTP-клиент RollyPay API
├── requirements.txt
├── .env.example
└── selectel-market.service # systemd unit
```

---

## Формат загрузки аккаунтов (в боте)

В админ-панели → «📚 Загрузить аккаунты» — вставьте построчно:

```
Название | Описание | Цена | Данные аккаунта
Selectel Basic | 500 бонусов, верифицирован | 300 | login@mail.ru:password123
Selectel Pro | 2000 бонусов, ключ API | 800 | apiuser@corp.ru:securepass:api_key_here
```

---

## Управление

```bash
# Перезапуск
sudo systemctl restart selectel-market

# Логи в реальном времени
sudo journalctl -u selectel-market -f

# Остановка
sudo systemctl stop selectel-market
```

---

## Тестирование платежей

Установите в `.env`:
```ini
ROLLYPAY_TEST_MODE=true
```

Тестовые платежи не списывают реальные деньги. Подробнее: https://docs.rollypay.io/api/testing
