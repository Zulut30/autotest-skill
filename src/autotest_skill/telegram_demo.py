"""Aiogram fixture with explicit state, callbacks and bounded duplicate handling."""

from collections import deque
from dataclasses import replace
from aiogram import Dispatcher, Router, F, BaseMiddleware
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class Collect(StatesGroup):
    name = State()
    confirm = State()


class Deduplicate(BaseMiddleware):
    def __init__(self):
        self.seen, self.order = set(), deque()

    async def __call__(self, handler, event, data):
        if event.update_id in self.seen:
            return None
        self.seen.add(event.update_id)
        self.order.append(event.update_id)
        if len(self.order)>1000:
            self.seen.remove(self.order.popleft())
        return await handler(event,data)


class LeakyStorage(MemoryStorage):
    """Intentional benchmark defect: all users share one state key."""
    def shared(self,key): return replace(key,user_id=1,chat_id=1)
    async def get_state(self,key): return await super().get_state(self.shared(key))
    async def set_state(self,key,state=None): return await super().set_state(self.shared(key),state)
    async def get_data(self,key): return await super().get_data(self.shared(key))
    async def set_data(self,key,data): return await super().set_data(self.shared(key),data)


def create_dispatcher(defects=False):
    dispatcher=Dispatcher(storage=LeakyStorage() if defects else MemoryStorage())
    dispatcher['items']=[]
    dispatcher.update.outer_middleware(Deduplicate())
    router=Router()

    @router.message(CommandStart())
    async def start(message):
        await message.answer('Welcome. Use /new to add an item.')

    @router.message(Command('help'))
    async def help_command(message):
        await message.answer('Commands: /start /new /cancel /admin')

    @router.message(Command('admin'))
    async def admin(message):
        await message.answer('Admin allowed' if message.from_user.id==9001 else 'Admin denied')

    @router.message(Command('cancel'))
    async def cancel(message,state:FSMContext):
        await state.clear()
        await message.answer('Cancelled')

    @router.message(Command('new'))
    async def new(message,state:FSMContext):
        await state.clear()
        await state.set_state(Collect.name)
        await message.answer('Enter item name.')

    @router.message(Collect.name,F.text,~F.text.startswith('/'))
    async def name(message,state:FSMContext):
        value=message.text.strip()
        if not value or len(value)>100:
            await message.answer('Name cannot be empty or exceed 100 characters.')
            return
        await state.update_data(name=value)
        await state.set_state(Collect.confirm)
        markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text='Confirm',callback_data='confirm'),
            InlineKeyboardButton(text='Cancel',callback_data='cancel')]])
        await message.answer('Confirm item: '+value,reply_markup=markup)

    @router.callback_query(F.data=='cancel')
    async def callback_cancel(query,state:FSMContext):
        await state.clear()
        await query.answer('Cancelled')
        await query.message.answer('Cancelled')

    @router.callback_query(F.data=='confirm',StateFilter(Collect.confirm))
    async def confirm(query,state:FSMContext,items:list):
        values=await state.get_data()
        items.append({'user_id':query.from_user.id,'chat_id':query.message.chat.id,'name':values['name']})
        await state.clear()
        await query.answer('Saved')
        await query.message.answer('Saved item: '+values['name'])

    @router.callback_query()
    async def stale(query):
        await query.answer('Button expired. Send /new.')

    @router.message()
    async def unknown(message):
        await message.answer('Unknown command. Use /help.')

    dispatcher.include_router(router)
    return dispatcher
