import tiktoken
import logging
import functools
import json
import math

logging.basicConfig(filename='logg_file.log', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%d-%b-%y %H:%M:%S', level=logging.INFO, encoding="UTF-8")


def split_messages(messages):
    answer_s = []
    this_pos = 0
    next_pos = 4096
    for i in range(0, (math.ceil(len(messages) / 4096))):
        counter = 0
        for j in messages[::-1]:
            counter += 1
            if j == " " or j == "\n":
                next_pos -= counter - 1
                break
        answer_s.append(messages[this_pos:next_pos])
        this_pos = next_pos
        next_pos += 4096

    answer_s.append(messages[this_pos:])
    return answer_s




def num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = 0
    for message in messages:
        num_tokens += 4
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += -1
    num_tokens += 2
    return num_tokens


def counter_mess(user_id):
    with open("users.json", 'r+') as f:
        users = json.loads(f.read())
        for index, user in enumerate(users):
            if user["chat_id"] == user_id:
                users[index]["count"] += 1
                break
        f.seek(0)
        f.write(json.dumps(users))


def logger(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logging.log(level=logging.INFO, msg=f"Calling {func.__name__} with args {args}")
        return func(*args, **kwargs)
    return wrapper


def is_reg(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        with open("users.json", 'r') as f:
            users = json.load(f)
            is_reg = any(user["chat_id"] == self.chat.id for user in users)
            if is_reg:
                return func(self, *args, **kwargs)
            else:
                return func({"error": "not registered", "user": self}, *args, **kwargs)
    return wrapper