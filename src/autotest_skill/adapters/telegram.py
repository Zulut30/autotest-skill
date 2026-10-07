"""Aiogram handler scenarios and explicit live-client prerequisites."""

import asyncio
import importlib
import re
import sys
from ..artifacts import write_json
from ..errors import Blocked

BUILTIN='autotest_skill.telegram_demo:create_dispatcher'


def scenario_events(name):
    message=lambda text,**kw: {'text':text,**kw}
    callback=lambda value,**kw: {'callback':value,**kw}
    return {
        'start':[message('/start'),message('/help'),message('/unknown')],
        'dialog':[message('/new'),message('Widget'),callback('confirm')],
        'invalid':[message('/new'),message(' ')],
        'cancel':[message('/new'),message('Widget'),callback('cancel')],
        'callback':[message('/new'),message('Widget'),callback('tampered'),callback('confirm'),callback('confirm')],
        'isolation':[message('/new'),message('Alice private'),message('Bob unrelated',user_id=502),message('Other chat',chat_id=-100501)],
        'duplicate':[message('/new',update_id=1),message('Widget',update_id=2),callback('confirm',update_id=3),callback('confirm',update_id=3)],
        'delivery':[message('/start'),message('/new'),message('Widget'),callback('confirm')],
    }[name]


async def local(check,context):
    from aiogram import Bot
    from ..telegram_transport import RecordingSession,update_event
    spec=check.spec
    if not re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:[A-Za-z_]\w*',spec.factory):
        raise Blocked('Invalid dispatcher factory reference')
    module,name=spec.factory.split(':')
    added=str(context.root) not in sys.path
    if added: sys.path.insert(0,str(context.root))
    try:
        factory=getattr(importlib.import_module(module),name)
    finally:
        if added: sys.path.remove(str(context.root))
    dispatcher=factory(defects=spec.defects) if spec.factory==BUILTIN else factory()
    session=RecordingSession()
    bot=Bot(token=f"{123456789}:{'A'*35}",session=session)
    events=[event.model_dump(exclude_none=True) for event in spec.events] if spec.events else scenario_events(spec.scenario)
    try:
        for index,event in enumerate(events,start=1):
            context.consume('actions')
            identifier=event.get('update_id',index)
            update=update_event(bot,identifier,text=event.get('text'),callback=event.get('callback'),
                                user_id=event.get('user_id',501),chat_id=event.get('chat_id'))
            if spec.scenario=='delivery':
                await dispatcher.feed_webhook_update(bot,update,_timeout=min(5,context.remaining()))
            else:
                await dispatcher.feed_update(bot,update)
        texts=[call['text'] for call in session.calls]
        items=dispatcher.get('items',[])
        states={}
        if spec.factory==BUILTIN:
            for label,user,chat in [('user_a',501,501),('user_b',502,502),('other_chat',501,-100501)]:
                states[label]=await dispatcher.fsm.get_context(bot=bot,chat_id=chat,user_id=user).get_state()
        expected=spec.expected_messages or {
            'start':['Welcome. Use /new to add an item.','Commands: /start /new /cancel /admin','Unknown command. Use /help.'],
            'dialog':['Saved item: Widget'], 'invalid':['Name cannot be empty or exceed 100 characters.'],
            'cancel':['Cancelled'], 'callback':['Button expired. Send /new.','Saved item: Widget'],
            'isolation':['Unknown command. Use /help.'], 'duplicate':['Saved item: Widget'],
            'delivery':['Saved item: Widget'],
        }[spec.scenario]
        matches=all(text in texts for text in expected)
        if spec.expected_text is not None:
            matches=matches and any(spec.expected_text in text for text in texts)
        if spec.factory==BUILTIN:
            if spec.scenario in {'dialog','callback','duplicate','delivery'}:
                matches=matches and len(items)==1 and items[0]['name']=='Widget' and states['user_a'] is None
            elif spec.scenario=='cancel': matches=matches and not items and states['user_a'] is None
            elif spec.scenario=='invalid': matches=matches and not items and states['user_a']=='Collect:name'
            elif spec.scenario=='isolation': matches=matches and states['user_a']=='Collect:confirm' and states['user_b'] is None and states['other_chat'] is None and not items
        actual={'mode':'local_recording_transport','calls':session.calls,'states':states,'items':items,
                'events_executed':len(events),'live_telegram_validated':False, 'delivery_entrypoint':'feed_webhook_update' if spec.scenario=='delivery' else 'feed_update'}
        artifact=f'{check.id}.telegram.json'
        write_json(context.folder,artifact,actual,context.redactor)
        return context.result(check,'passed' if matches else 'failed',expected={'messages':expected},actual=actual,
            reason='' if matches else 'Bot replies, states or side effects violate the declared scenario',evidence=[artifact])
    finally:
        await dispatcher.storage.close()
        await session.close()


def run(check,context):
    if check.spec.mode=='live':
        from ..telegram_live import run_live
        return asyncio.run(asyncio.wait_for(run_live(check,context),timeout=min(check.spec.timeout,context.remaining())))
    return asyncio.run(asyncio.wait_for(local(check,context),timeout=min(check.spec.timeout,context.remaining())))
