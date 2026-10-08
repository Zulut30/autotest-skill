"""Recording transport exercises aiogram while explicitly avoiding Telegram networking."""

from datetime import UTC, datetime

from aiogram.client.session.base import BaseSession
from aiogram.methods import AnswerCallbackQuery, EditMessageText, GetMe, SendMessage
from aiogram.types import CallbackQuery, Chat, Message, MessageEntity, Update, User

from .errors import Blocked


class RecordingSession(BaseSession):
    def __init__(self):
        super().__init__()
        self.calls = []
        self.closed = False

    async def close(self):
        self.closed = True

    async def stream_content(self, *args, **kwargs):
        raise Blocked("Media transport is outside the local adapter scope")
        yield b""

    async def make_request(self, bot, method, timeout=None):
        name = method.__api_method__
        if isinstance(method, GetMe):
            return User(id=bot.id, is_bot=True, first_name="Fixture", username="fixture_bot")
        if isinstance(method, AnswerCallbackQuery):
            self.calls.append(
                {"method": name, "text": method.text or "", "callback_id": method.callback_query_id}
            )
            return True
        if isinstance(method, (SendMessage, EditMessageText)):
            markup = getattr(method, "reply_markup", None)
            buttons = []
            if markup and hasattr(markup, "inline_keyboard"):
                buttons = [
                    {"text": button.text, "data": button.callback_data}
                    for row in markup.inline_keyboard
                    for button in row
                ]
            self.calls.append(
                {"method": name, "text": method.text, "chat_id": method.chat_id, "buttons": buttons}
            )
            return Message(
                message_id=len(self.calls),
                date=datetime.now(UTC),
                chat=Chat(
                    id=int(method.chat_id), type="private" if int(method.chat_id) > 0 else "group"
                ),
                from_user=User(id=bot.id, is_bot=True, first_name="Fixture"),
                text=method.text,
            )
        raise Blocked(f"Local transport does not implement Bot API method {name}")


def update_event(bot, identifier, text=None, callback=None, user_id=501, chat_id=None):
    chat_id = user_id if chat_id is None else chat_id
    user = User(id=user_id, is_bot=False, first_name="Test user")
    chat = Chat(id=chat_id, type="private" if chat_id > 0 else "group")
    now = datetime.now(UTC)
    if callback is not None:
        message = Message(
            message_id=1,
            date=now,
            chat=chat,
            from_user=User(id=bot.id, is_bot=True, first_name="Fixture"),
            text="Fixture button",
        )
        return Update(
            update_id=identifier,
            callback_query=CallbackQuery(
                id=f"callback-{identifier}",
                from_user=user,
                chat_instance="isolated-fixture",
                message=message,
                data=callback,
            ),
        )
    entities = (
        [MessageEntity(type="bot_command", offset=0, length=len(text.split()[0]))]
        if text and text.startswith("/")
        else []
    )
    return Update(
        update_id=identifier,
        message=Message(
            message_id=identifier,
            date=now,
            chat=chat,
            from_user=user,
            text=text or "",
            entities=entities,
        ),
    )
