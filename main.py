import openai
from decouple import config
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from utils import num_tokens_from_messages, logger, is_reg, counter_mess
from aiogram.utils import executor, markdown
import json

openai.api_key = config("OPENAI_API_KEY")

max_response_tokens = 250
token_limit = 4096

API_TOKEN = config("BOT_TOKEN")
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

temp_history = []


@dp.message_handler(commands='start')
@logger
async def cmd_start(message: types.Message, *args, **kwargs):
    await bot.send_message(message.chat.id,
                           "Пропиши команду /reg включиться режим общения и можешь начинать спрашивать)")


@dp.message_handler(commands='reg')
@logger
async def cmd_gpt(message: types.Message, *args, **kwargs):
    with open("users.json", 'r+') as f:
        users = json.loads(f.read())
        is_registerd = bool(list(filter(lambda x: x["chat_id"] == message.chat.id, users)))
        if is_registerd:
            await bot.send_message(message.chat.id, "Вы уже зарегистрированы!")
        else:
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text="Да",
                                           callback_data="reg-%s-%s" % (message.chat.id, message.chat.username)),
                types.InlineKeyboardButton(text="Нет",
                                           callback_data="unreg-%s-%s" % (message.chat.id, message.chat.username))
            )
            await bot.send_message(message.chat.id, "Проводим регистрацию. Подождите!")
            await bot.send_message(734264203, "Пользователь @%s хочет зарегистрироваться!" % message.from_user.username,
                                   reply_markup=keyboard)


@dp.callback_query_handler(lambda call: True)
@logger
async def callback_inline(call: types.CallbackQuery):
    data = call.data.split('-')
    if data[0] == "reg":
        with open("users.json", 'r+') as f:
            users = json.loads(f.read())
            users.append({"chat_id": int(data[1]), "username": data[2], "count": 0})
            f.seek(0)
            f.write(json.dumps(users))
        await bot.send_message(chat_id=int(data[1]), text="Вы зарегистрированы!")
        await bot.edit_message_text(chat_id=734264203, message_id=call.message.message_id,
                                    text="Пользователь @%s зарегистрирован!" % data[2])
    if data[0] == "unreg":
        await bot.send_message(chat_id=int(data[1]), text="Вы НЕ зарегистрированы!")
        await bot.edit_message_text(chat_id=734264203, message_id=call.message.message_id,
                                    text="Пользователь @%s НЕ зарегистрирован!" % data[2])
    if data[0] == "rehistory":
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=call.message.text)
        await bot.send_message(chat_id=call.message.chat.id, text="История сброшена")
        index_history = [(index, history) for index, history in enumerate(temp_history) if int(data[1]) in history]
        if bool(index_history):
            temp_history[index_history[0][0]][data[1]] = [{"role": "system", "content": "You are a helpful assistant."}]


@dp.message_handler(commands='gpt')
@logger
@is_reg
async def cmd_gpt(message: types.Message, *args, **kwargs):
    if "error" in message:
        if message['error'] == "not registered":
            await bot.send_message(message['user'].chat.id, "Вы не зарегистрированы! пропишите /reg")
    else:
        if not bool(list(filter(lambda x: message.chat.id in x, temp_history))):
            temp_history.append({message.chat.id: [{"role": "system", "content": "You are a helpful assistant."}]})
        await bot.send_message(message.chat.id, "Можете начать диалог!")


@dp.message_handler(content_types='text')
@logger
@is_reg
async def dialog(message: types.Message, *args, **kwargs):
    if "error" in message:
        if message['error'] == "not registered":
            await bot.send_message(message['user'].chat.id, "Вы не зарегистрированы! пропишите /reg")
    else:
        index_history = [(index, history) for index, history in enumerate(temp_history) if message.chat.id in history]
        if bool(index_history):
            index_history=index_history[0]
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(
                types.InlineKeyboardButton(text="Сбросить историю",
                                           callback_data="rehistory-%s-%s" % (message.chat.id, message.chat.username)),
            )
            temp_history[index_history[0]][message.chat.id].append({"role": "user", "content": message.text})
            conv_history_tokens = num_tokens_from_messages(temp_history[index_history[0]][message.chat.id])
            while conv_history_tokens + max_response_tokens >= token_limit:
                del temp_history[index_history[0]][message.chat.id][1]
                conv_history_tokens = num_tokens_from_messages(temp_history[index_history[0]][message.chat.id])
            print(conv_history_tokens)
            await bot.send_message(message.chat.id, "Ждём ответа...")
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=temp_history[index_history[0]][message.chat.id]
            )
            counter_mess(message.chat.id)
            answer = markdown.escape_md(str(response['choices'][0]['message']['content']))
            # for c in ['-', '\\', '-', '.', '?', '(', ')', '[', ']', '{', '}', '!', '~', '@', '#']:
            #     answer = answer.replace(c, "\\" + c)
            temp_history[index_history[0]][message.chat.id].append({"role": "assistant", "content": response['choices'][0]['message']['content']})
            await bot.send_message(message.chat.id, answer, reply_markup=keyboard, parse_mode="MarkdownV2")
        else:
            await bot.send_message(message.chat.id, "Пропишите команду /gpt")


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
