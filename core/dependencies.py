from multiprocessing import Queue
from aiogram import Bot

is_delete_ad = False
is_delete_bw = False

classify_queue = Queue()
result_queue = Queue()
bot = None  # Initialize as None, will be set later