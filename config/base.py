# Please, insert your bot api key, provided by the BotFather.
TELEGRAM_BOT_KEY = "455448121:AAES_lCFjeZaLSe3_Sy03638jJJT0yvMWnc"

ENABLE_WEBHOOK = False

WEBHOOK_PORT = 80
WEBHOOK_URL = "http://example.com/"
WEBHOOK_CERT = None
WEBHOOK_CERT_KEY = None

INSTRUCTIONS_MSG="""
Привет! Я инлайновый бот, который поможет тебе найти стикеры с самыми хайповыми цитатами Сергея Дружко.

Чтобы использовать меня, введи в любом чате мое имя @druzhbot, затем начало цитаты, и я пришлю тебе стикеры, которые найду.

Я знаю стикеров: *{stickers_count}*.

К сожалению, больше мне сказать нечего. Это все, чему меня научили.
""".strip()

STICKER_DATA_MSG="""
File ID: `{file_id}`

Это тайное заклинание для адептов ордена Telegram Bot API. Никому не говори, что ты видел!
""".strip()

HYPE_MSG="Ммм... Я вижу, ты уже хайпанул немножко 😉"
