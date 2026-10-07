"""Real Telegram user client; never prompt for login or persist session strings."""

import asyncio
import os
from .errors import Blocked


async def run_live(check,context):
    from aiogram import Bot, F
    from aiogram.client.session.aiohttp import AiohttpSession
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    from .artifacts import write_json
    from .adapters.telegram import scenario_events
    from .telegram_demo import create_dispatcher
    spec=check.spec
    token=context.redactor.binding('TG_BOT_TOKEN')
    identifier=context.redactor.binding('TG_API_ID')
    api_hash=context.redactor.binding('TG_API_HASH')
    session_value=context.redactor.binding('TG_SESSION')
    try:
        api_id=int(identifier)
        string_session=StringSession(session_value)
    except (ValueError,TypeError) as exc:
        raise Blocked('Telegram bindings require a numeric API ID and preauthorized StringSession') from exc
    if spec.scenario=='isolation':
        raise Blocked('Live isolation requires a separately configured second test-user session')
    class BoundedSession(AiohttpSession):
        async def make_request(self,*args,**kwargs):
            context.consume('requests')
            return await super().make_request(*args,**kwargs)
    transport=BoundedSession(proxy=os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy'))
    bot=Bot(token=token,session=transport)
    client=TelegramClient(string_session,api_id,api_hash,timeout=min(spec.timeout,context.remaining()),
                          connection_retries=0,request_retries=0)
    dispatcher=None
    polling=None
    replies=[]
    try:
        identity=await bot.get_me()
        username=spec.bot_username or identity.username
        if not username or username.lstrip('@')!=identity.username:
            raise Blocked('Configured live bot does not match the supplied bot token')
        await client.connect()
        if not await client.is_user_authorized():
            raise Blocked('Telegram user session is not authorized; supply a preauthorized session securely')
        user=await client.get_me()
        if user.bot:
            raise Blocked('A genuine test-user session is required; Bot API cannot imitate a user')
        if spec.serve_fixture:
            webhook=await bot.get_webhook_info()
            if webhook.url:
                raise Blocked('Test bot has an existing webhook; its configuration will not be overwritten')
            dispatcher=create_dispatcher()
            dispatcher.sub_routers[0].message.filter(F.from_user.id==user.id)
            dispatcher.sub_routers[0].callback_query.filter(F.from_user.id==user.id)
            polling=asyncio.create_task(dispatcher.start_polling(bot,polling_timeout=1,handle_signals=False,close_bot_session=False))
        events=[event.model_dump(exclude_none=True) for event in spec.events] if spec.events else scenario_events(spec.scenario)
        expected=spec.expected_messages or ({'start':['Welcome. Use /new to add an item.','Commands: /start /new /cancel /admin','Unknown command. Use /help.'],
                                             'dialog':['Saved item: Widget'],'cancel':['Cancelled']} if spec.serve_fixture else {}).get(spec.scenario)
        if not expected:
            raise Blocked('Live checks need explicit expected replies or a supported fixture scenario')
        latest=None
        async with client.conversation(username,timeout=min(spec.timeout,context.remaining())) as conversation:
            for event in events:
                context.consume('actions')
                if event.get('callback') is not None:
                    if latest is None or not latest.buttons:
                        raise Blocked('Expected inline button message is unavailable')
                    await latest.click(data=event['callback'].encode())
                else:
                    await conversation.send_message(event.get('text',''))
                latest=await conversation.get_response()
                replies.append(latest.raw_text)
        matches=all(text in replies for text in expected)
        if spec.expected_text is not None:
            matches=matches and any(spec.expected_text in text for text in replies)
        actual={'mode':'live_telegram','bot':username,'replies':replies,'events_executed':len(events),
                'live_telegram_validated':matches,'wire_request_count_complete':False,
                'scope':'One authenticated test user; client-library protocol frames are not counted as HTTP requests.'}
        artifact=f'{check.id}.telegram-live.json'
        write_json(context.folder,artifact,actual,context.redactor)
        return context.result(check,'passed' if matches else 'failed',expected={'messages':expected},actual=actual,
            evidence=[artifact],reason='' if matches else 'Live bot replies violate the explicit scenario')
    finally:
        if polling is not None:
            polling.cancel()
            await asyncio.gather(polling,return_exceptions=True)
        if dispatcher is not None: await dispatcher.storage.close()
        await client.disconnect()
        await bot.session.close()
