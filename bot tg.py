import asyncio
import datetime
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- НАСТРОЙКИ ---
API_TOKEN = '8321465899:AAEvcc20bhe6-UYsILT3BL1ZkoHe_MBHiIo'  # Обязательно смени токен!
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---
def init_db():
    conn = sqlite3.connect('deals.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS deals
                      (
                          user_id
                          TEXT,
                          date
                          TEXT,
                          name
                          TEXT,
                          category
                          TEXT,
                          okup
                          TEXT,
                          pocket
                          TEXT,
                          reinvest
                          TEXT
                      )''')
    conn.commit()
    conn.close()


init_db()


# --- СОСТОЯНИЯ ---
class DealState(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_quantity = State()
    waiting_for_buy = State()
    waiting_for_sell = State()
    waiting_for_sold_quantity = State()
    waiting_for_delivery = State()
    waiting_for_reinvest = State()


# --- КОМАНДЫ И ЛОГИКА ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await message.answer("Салам! Пиши название товара для начала сделки.\n\n"
                         "Команды:\n'очисти' — удалить историю\n'статистика' — глянуть сделки")
    await state.set_state(DealState.waiting_for_name)


@dp.message(F.text.lower() == "очисти")
async def clear_data(message: types.Message):
    conn = sqlite3.connect('deals.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM deals WHERE user_id = ?", (str(message.from_user.id),))
    conn.commit()
    conn.close()
    await message.answer("Твоя история удалена из базы, бро!")


@dp.message(F.text.lower() == "статистика")
async def show_stats(message: types.Message):
    conn = sqlite3.connect('deals.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deals WHERE user_id = ?", (str(message.from_user.id),))
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        await message.answer("У тебя пока нет записей.")
        return

    report = "Твои сделки:\n"
    for row in rows:
        report += f"{row[1]} | {row[2]} | Прибыль: {row[4]} | На закуп: {row[6]}\n"
    await message.answer(report)


# --- БЛОК СДЕЛКИ (твоя логика остается такой же) ---
@dp.message(DealState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Какая категория?")
    await state.set_state(DealState.waiting_for_category)


@dp.message(DealState.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    await state.update_data(category=message.text)
    await message.answer("Сколько штук закупил?")
    await state.set_state(DealState.waiting_for_quantity)


@dp.message(DealState.waiting_for_quantity)
async def process_q(message: types.Message, state: FSMContext):
    try:
        await state.update_data(quantity=int(message.text))
        await message.answer("Цена закупки за 1 шт?")
        await state.set_state(DealState.waiting_for_buy)
    except:
        await message.answer("Цифрами, бро!")


@dp.message(DealState.waiting_for_buy)
async def process_buy(message: types.Message, state: FSMContext):
    await state.update_data(buy=int(message.text))
    await message.answer("Цена продажи за 1 шт?")
    await state.set_state(DealState.waiting_for_sell)


@dp.message(DealState.waiting_for_sell)
async def process_sell(message: types.Message, state: FSMContext):
    await state.update_data(sell=int(message.text))
    await message.answer("Сколько штук продал?")
    await state.set_state(DealState.waiting_for_sold_quantity)


@dp.message(DealState.waiting_for_sold_quantity)
async def process_sold_q(message: types.Message, state: FSMContext):
    await state.update_data(sold_q=int(message.text))
    await message.answer("Расходы на такси/прочее?")
    await state.set_state(DealState.waiting_for_delivery)


@dp.message(DealState.waiting_for_delivery)
async def process_delivery(message: types.Message, state: FSMContext):
    data = await state.get_data()
    okup = (data['sell'] * int(message.text)) - (data['buy'] * int(message.text)) - int(message.text)
    await state.update_data(okup=okup)
    await message.answer(f"Прибыль: {okup} тенге. Сколько берешь на закуп?")
    await state.set_state(DealState.waiting_for_reinvest)


@dp.message(DealState.waiting_for_reinvest)
async def final_calc(message: types.Message, state: FSMContext):
    reinvest = int(message.text)
    data = await state.get_data()
    okup = data['okup']
    cash_in_pocket = okup - reinvest
    vremya = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    conn = sqlite3.connect('deals.db')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO deals VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (str(message.from_user.id), vremya, data['name'], data['category'], str(okup), str(cash_in_pocket),
                    str(reinvest)))
    conn.commit()
    conn.close()

    await message.answer("Готово! Запись сохранена в базу.")
    await state.clear()


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())