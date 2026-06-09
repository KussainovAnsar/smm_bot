# SMM Bot: AI Content Assistant for Telegram

MVP Telegram-бота, который превращает голосовые сообщения, текст и фото в готовые варианты контента для Instagram, Threads и Telegram.

## Что умеет MVP

- Принимает текст, voice-сообщения и фото.
- Расшифровывает voice через OpenAI speech-to-text.
- Генерирует 2-3 варианта поста: hook, основной текст, CTA, хэштеги.
- Поддерживает форматы: экспертный, личный, продающий, storytelling.
- Анализирует присланные фото и выбирает лучшие для публикации.
- Если фото нет, предлагает визуальную концепцию и prompt для AI-картинки.
- Помнит базовую персонализацию: ниша, tone of voice, стиль.
- Поддерживает доработки: "сделай короче", "сделай дерзко", "добавь продажу", "перепиши".
- Генерирует контент-план на неделю или месяц.

## Быстрый старт

1. Создайте Telegram-бота через [BotFather](https://t.me/BotFather) и получите токен.
2. Создайте `.env` рядом с `.env.example`:

```powershell
Copy-Item .env.example .env
```

3. Заполните `TELEGRAM_BOT_TOKEN` и `OPENAI_API_KEY`.
4. Установите зависимости:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

5. Запустите бота:

```powershell
python -m src.smm_bot.bot
```

## Деплой на VPS

Бот работает в режиме long-polling (только исходящие соединения, без портов и
домена). Готовые Docker-артефакты и пошаговая инструкция — в [DEPLOY.md](DEPLOY.md):

```bash
cp .env.example .env   # заполнить токены
docker compose up -d --build
```

## Команды

- `/start` - старт и краткая инструкция.
- `/profile` - показать текущую персонализацию.
- `/setprofile ниша | tone | стиль` - сохранить персонализацию.
- `/plan week` - контент-план на неделю.
- `/plan month` - контент-план на месяц.

Примеры:

```text
/setprofile фитнес-тренер | уверенно, дружелюбно | коротко, с личными примерами
/plan week
```

## Как пользоваться

Отправьте боту:

- voice с идеей поста;
- текст с заметками;
- одно или несколько фото;
- команду на доработку после генерации.

Бот вернет варианты постов и визуальную рекомендацию.

## Бесплатные AI-провайдеры для MVP

По умолчанию проект настроен на Gemini:

- `AI_PROVIDER=gemini`
- `GEMINI_MODEL=gemini-2.5-flash`

Gemini подходит для MVP, потому что у него есть бесплатный tier в Google AI Studio и сильный multimodal API: текст, фото и аудио можно обрабатывать одной моделью.

Чтобы включить Gemini:

1. Создайте API key в [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Вставьте его в `.env`:

```env
AI_PROVIDER=gemini
GEMINI_API_KEY=ваш_ключ
GEMINI_MODEL=gemini-2.5-flash
```

Groq тоже поддерживается:

- `GROQ_TEXT_MODEL=llama-3.3-70b-versatile`
- `GROQ_TRANSCRIBE_MODEL=whisper-large-v3`
- `GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct`

Чтобы включить Groq:

1. Зарегистрируйтесь в [Groq Console](https://console.groq.com/).
2. Создайте API key.
3. Вставьте его в `.env`:

```env
AI_PROVIDER=groq
GROQ_API_KEY=ваш_ключ
```

## Настройки OpenAI как fallback

OpenAI можно оставить как запасной вариант:

```env
AI_PROVIDER=openai
OPENAI_API_KEY=ваш_ключ
OPENAI_TEXT_MODEL=gpt-5.2
OPENAI_TRANSCRIBE_MODEL=gpt-4o-mini-transcribe
OPENAI_IMAGE_MODEL=gpt-image-1.5
```

Чтобы включить генерацию и отправку AI-картинки, установите:

```env
OPENAI_ENABLE_IMAGE_GENERATION=true
```

Если генерация изображений выключена, бот все равно возвращает готовый prompt для визуала.
