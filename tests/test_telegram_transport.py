import asyncio
from aiogram import Bot
from autotest_skill.telegram_demo import create_dispatcher
from autotest_skill.telegram_transport import RecordingSession,update_event


def test_real_dispatcher_consumes_events_with_recorded_api_calls():
    async def scenario():
        session=RecordingSession()
        bot=Bot(token=f"{123456789}:{'A'*35}",session=session)
        dispatcher=create_dispatcher()
        for identifier,text in enumerate(('/new','Widget'),start=1):
            await dispatcher.feed_update(bot,update_event(bot,identifier,text=text))
        await dispatcher.feed_update(bot,update_event(bot,3,callback='confirm'))
        assert dispatcher['items']==[{'user_id':501,'chat_id':501,'name':'Widget'}]
        assert any(call['text']=='Saved item: Widget' for call in session.calls)
        assert any(call['method']=='answerCallbackQuery' and call['text']=='Saved' for call in session.calls)
        await dispatcher.storage.close();await session.close()
        assert session.closed
    asyncio.run(scenario())
