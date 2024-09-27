import csv
import re


AD_PATTERNS_FILE = 'txts/base/ad_patterns.csv'
ADMINS_FILE = 'txts/base/admins_list.txt'
BAD_WORDS_FILE = 'txts/base/bad_words.txt'
DELETE_LIST_FILE = 'txts/base/delete_list.txt'
WHITE_LIST_FILE = 'txts/base/white_list.txt'

ADMIN_ACTIONS_FILE = 'txts/admin_actions.csv'
BAN_LIST_FILE = "txts/ban_list.csv"
BAN_CANDIDATES_FILE = "txts/ban_candidates.csv"
DELETED_AD_FILE = "txts/deleted_ad.txt"
DELETED_BW_FILE = "txts/deleted_bw.txt"

MATCH_THRESHOLD = 1
MESSAGE_TIMEOUT = 60  # seconds

adminsId = []
bad_words = []
white_list = []
delete_list = []
ad_patterns = []


# --- Загрузка данных ---
def load_data():
    global adminsId, bad_words, white_list, delete_list, ad_patterns

    try:
        with open(ADMINS_FILE, 'r') as f:
            adminsId = [int(line.strip()) for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        print(f"Файл {ADMINS_FILE} не найден. Создайте файл и добавьте ID админов.")
        adminsId = []
    except Exception as e:
        print(f"Ошибка при загрузке {ADMINS_FILE}: {e}")
        adminsId = []

    try:
        with open(BAD_WORDS_FILE, "r", encoding='utf-8') as f:
            bad_words = [word.replace("\n", "").strip() for word in f.readlines()]
    except FileNotFoundError:
        print(f"Файл {BAD_WORDS_FILE} не найден. Создайте файл и добавьте нежелательные слова.")
        bad_words = []
    except Exception as e:
        print(f"Ошибка при загрузке {BAD_WORDS_FILE}: {e}")
        bad_words = []

    try:
        with open(WHITE_LIST_FILE, "r", encoding='utf-8') as f:
            white_list = [word.replace("\n", "").strip() for word in f.readlines()]
    except FileNotFoundError:
        print(f"Файл {WHITE_LIST_FILE} не найден. Создайте файл и добавьте разрешенные слова.")
        white_list = []
    except Exception as e:
        print(f"Ошибка при загрузке {WHITE_LIST_FILE}: {e}")
        white_list = []

    try:
        with open(DELETE_LIST_FILE, "r", encoding='utf-8') as f:
            delete_list = [word.strip() for word in f.readlines() if word.strip()]
    except FileNotFoundError:
        print(f"Файл {DELETE_LIST_FILE} не найден. Создайте файл и добавьте слова для удаления.")
        delete_list = []
    except Exception as e:
        print(f"Ошибка при загрузке {DELETE_LIST_FILE}: {e}")
        delete_list = []

    try:
        with open(AD_PATTERNS_FILE, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            ad_patterns = [re.compile(r'' + row[0], re.IGNORECASE) for row in reader if row]
    except FileNotFoundError:
        print(f"Файл {AD_PATTERNS_FILE} не найден. Создайте файл и добавьте паттерны рекламы.")
        ad_patterns = []
    except Exception as e:
        print(f"Ошибка при загрузке {AD_PATTERNS_FILE}: {e}")
        ad_patterns = []

load_data()