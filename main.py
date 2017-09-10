#!/usr/bin/env python3
import random
import sys
import time
from functools import wraps
from typing import List, Callable, Any, Dict

import structlog
from telegram import Bot, Update, InlineQueryResultCachedSticker
from telegram.ext import Updater, MessageHandler, InlineQueryHandler, Filters

import config


def rename_event_logproc(
        _logger: Any,
        _method: str,
        event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Structlog processor, renaming 'event' key to '_event', so it would
    always be the first one when keys are sorted.
    """

    if 'event' in event_dict:
        event_dict['_event'] = event_dict['event']
        del event_dict['event']

    return event_dict


logger = structlog.wrap_logger(
    structlog.PrintLogger(),
    processors=[
        rename_event_logproc,
        structlog.processors.JSONRenderer(sort_keys=True),
    ],
)


def into_words(q: str) -> List[str]:
    # Remove all syntax symbols
    syntax_marks = ",.!?-"
    for sym in syntax_marks:
        q = q.replace(sym, ' ')

    # Split into words
    words = q.lower().strip().split()
    words = [w.strip() for w in words]
    words = [w for w in words if w]

    return words


def word_in_words(word: str, words: List[str]) -> bool:
    for w in words:
        if w.startswith(word):
            return True
    return False


def search_stickers(query: str) -> List[str]:
    query_words = into_words(query)

    stickers = []
    for file_id, texts in config.STICKERS.items():
        texts_string = " ".join(texts).lower()
        texts_words = into_words(texts_string)
        if all([ word_in_words(w, texts_words) for w in query_words ]):
            stickers.append(file_id)

    return stickers


def random_stickers(n: int) -> List[str]:
    ids = list(config.STICKERS.keys())
    random.shuffle(ids)
    return ids[:n]


def log_exceptions(f: Callable):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error("Exception caught",
                type=type(e).__qualname__,
                value=str(e),
                func=f.__name__)
    return wrapper


@log_exceptions
def on_query(bot: Bot, update: Update):
    # This constant is defined by the Bot API.
    MAX_RESULTS = 50

    inline_query = update.inline_query

    if not inline_query:
        return

    # If query is empty - return random stickers.
    return_random = not inline_query.query

    logger.info("Inline query received",
        from_id=inline_query.from_user.id,
        from_name=inline_query.from_user.first_name,
        text=inline_query.query)

    if return_random:
        stickers = random_stickers(MAX_RESULTS)
    else:
        stickers = search_stickers(inline_query.query)

    if len(stickers) > MAX_RESULTS:
        stickers = stickers[:MAX_RESULTS]

    results = [InlineQueryResultCachedSticker(fid, fid) for fid in stickers]

    cache_time = 600
    if return_random:
        # Do not cache random results.
        cache_time = 0

    bot.answer_inline_query(inline_query.id, results, cache_time=cache_time)


@log_exceptions
def on_message(bot: Bot, update: Update):
    message = update.message

    if not message:
        return

    msg_logger = logger.bind(
        from_id=message.from_user.id,
        from_name=message.from_user.name)

    is_sticker = bool(message.sticker)
    sticker_is_in_db = is_sticker and message.sticker.file_id in config.STICKERS

    if sticker_is_in_db:
        msg_logger.info("Sticker received",
            file_id=message.sticker.file_id,
            known=True)

        bot.send_message(
            message.chat.id,
            config.HYPE_MSG,
            parse_mode='Markdown')
    elif is_sticker:
        msg_logger.info("Sticker received",
            file_id=message.sticker.file_id,
            known=False)

        bot.send_message(
            message.chat.id,
            config.STICKER_DATA_MSG.format(file_id=message.sticker.file_id),
            parse_mode='Markdown')
    else:
        msg_logger.info("Text message received",
            text=message.text)

        bot.send_message(
            message.chat.id,
            config.INSTRUCTIONS_MSG.format(stickers_count=len(config.STICKERS)),
            parse_mode='Markdown')


def check_stickers_integrity(chat_id: int, interval: float = 0.5):
    """
    This command sends every sticker from the db to the specified chat and
    reports when sending has failed (e.g. due to invalid file_id).
    """
    if not config.TELEGRAM_BOT_KEY:
        raise RuntimeError("Please, put you bot api key into the config.")

    bot = Bot(config.TELEGRAM_BOT_KEY)

    sticker_exceptions = {}
    for i, file_id in enumerate(config.STICKERS.keys()):
        iter_logger = logger.bind(
            current=i+1,
            total=len(config.STICKERS))

        iter_logger.info("Integrity check progresses")

        try:
            bot.send_sticker(chat_id, file_id)
        except Exception as e:
            sticker_exceptions[file_id] = e
            iter_logger.error("Sticker integrity check failed",
                file_id=file_id,
                exc_type=type(e).__qualname__,
                exc_value=str(e))

        time.sleep(interval)

    logger.info("Integrity check finished",
        failed=len(sticker_exceptions),
        total=len(config.STICKERS))

    for file_id, exc in sticker_exceptions.items():
        print("{} - {}: {}".format(file_id, type(exc).__qualname__, str(exc)))


def main():
    if not config.TELEGRAM_BOT_KEY:
        raise RuntimeError("Please, put you bot api key into the config.")

    updater = Updater(token=config.TELEGRAM_BOT_KEY)
    dispatcher = updater.dispatcher

    query_handler = InlineQueryHandler(on_query)
    dispatcher.add_handler(query_handler)

    msg_handler = MessageHandler(Filters.all, on_message)
    dispatcher.add_handler(msg_handler)

    if config.ENABLE_WEBHOOK:
        logger.info("Instance started",
            sticker_in_db=len(config.STICKERS),
            mode='webhook',
            webhook_url=config.WEBHOOK_URL)

        updater.start_webhook(
            listen='0.0.0.0',
            port=config.WEBHOOK_PORT,
            webhook_url=config.WEBHOOK_URL,
            cert=config.WEBHOOK_CERT,
            key=config.WEBHOOK_CERT_KEY)
        updater.bot.set_webhook(config.WEBHOOK_URL)
    else:
        logger.info("Instance started",
            sticker_in_db=len(config.STICKERS),
            mode='polling')

        updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main()
    elif sys.argv[1] == 'check_stickers_integrity':
        chat_id = int(sys.argv[2])
        check_stickers_integrity(chat_id)
