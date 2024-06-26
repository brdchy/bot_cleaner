import re

def extract_regular_chars(text):
    regular_chars = re.sub('[^a-zA-Zа-яА-Я0-9\s]', '', text)

    return regular_chars

ad_patterns = [
    re.compile(r'[iи]щ[уy] лю[dд][еёe]й для [dд][oо]п за[рp][aа][бb6][oо]тк[aа]', re.IGNORECASE),
    re.compile(r'[нn]а [уy][dд]ал[еёe][нn][нn]ой о[cс][нn][оo][вb][еёe]', re.IGNORECASE),
    re.compile(r'[вb] [cс][вb][oо][бb6][oо][dд][нn][oо][еёe] [вb][рp][еёe][мm]я', re.IGNORECASE),
    re.compile(r'п[oо][dд][рp][оo][бb6][нn][oо][cс]т[iи] [вb] л[iи][ч4][нn]ы[еёe] [cс][oо][oо][бb6]щ[еёe][нn][iи]я', re.IGNORECASE),
    re.compile(r'[уy][dд][aа]л[еёe][нn][нn][aа]я [рp][aа][бb6][oо]т[aа]', re.IGNORECASE),
    re.compile(r'кт[oо] [iи]щ[еёe]т п[oо][dд][рp][aа][бb6][oо]тк[уy]', re.IGNORECASE),
    re.compile(r'[рp][aа][b6б][oо]т[aаеe] [нn][aа] [dд][oо][мm][уy]', re.IGNORECASE),
    re.compile(r'[dд]ля п[oо]л[уy][ч4][еёe][нn][iи]я [dд][oо]п(?:\.?\s*|[oо]л[нn][iи]т[еёe]ль[нn][oо]г[oо]\s+)[dд][oо]х[oо][dд][aа]', re.IGNORECASE),
    re.compile(r'[iи]щ[уy] п[аa][рp]т[нn][ёеe][рp][оo][вb] [вb] к[оo][мm][аa][нn][дd][уy]', re.IGNORECASE),
    re.compile(r'[сc] (?:т[еe]л[еe]ф[оo][нn][аa]|к[оo][мm]п[ьb]ю?т[еe][рp][аa])', re.IGNORECASE),
    re.compile(r'[оo]т\s*1?[8\u0038\u0030\u03a3\u0417]\s*л[еe]т,?\s*[чч4][аa][сc]т[iи][чч4][нn][аa]я\s*з[аa][нn]ят[оo][сc]т[ьb]', re.IGNORECASE),
    re.compile(r'х[оo][рp][оo]ш[иi]й\s*[дd][оo]п[оo]л[нn][иi]т[еe]л[ьb][нn]ый\s*з[аa][рp][аa][бb6][оo]т[оo]к', re.IGNORECASE),
    re.compile(r'[рp][aа][бb6][oо]т[aа] [нn][aа] [уy][dд][aа]л[еёe][нn][кk][еёe]', re.IGNORECASE),
    re.compile(r'[гg][иi][бb6][кk][иi]й [гg][рp][aа][фf][иi][кk]', re.IGNORECASE),
    re.compile(r'[сc][вb][oо][бb6][oо][dд][нn]ый [гg][рp][aа][фf][иi][кk]', re.IGNORECASE),
    re.compile(r'[dд][иi][сc]т[aа][нn]ц[иi][oо][нn][нn][aа]я [рp][aа][бb6][oо]т[aа]', re.IGNORECASE),
    re.compile(r'[рp][aа][бb6][oо]т[aа] [иi]з [dд][oо][мm][aа]', re.IGNORECASE),
    re.compile(r'[пn][оo][dд][рp][оo][бb6][нn][оo][сc]т[иi] [вb] л[иi][чч4][кk][уy]', re.IGNORECASE),
    re.compile(r'[пn][оo][dд][рp][оo][бb6][нn][оo][сc]т[иi] [вb] л[cс]', re.IGNORECASE),
    re.compile(r'[вb][сc][еeё] [dд][еeё]т[аa]л[иiu] [вb] л[сc]', re.IGNORECASE),
    re.compile(r'[вb] п[оo][иiеu][сc]к[еe] лю[дd][еeё]й', re.IGNORECASE),
    re.compile(r'з[аa][иiеu][нn]т[еe]р[еe][сc][оo][вb][аa][нn](?:[нn]ы[хйемe]?|[вb]ш[иiе][хйемe]?ся)? (?:[вb]|[нn][аa]) п[аa][сc][сc][иiеu][вb][нn](?:[оo]й|[уy]ю|[аa]я|[ыоo][хйемe]?) (?:пр[иiеu][бb6][ыу]л[ьb]?|[дd][оo]х[оo][дd])[иiеu]?', re.IGNORECASE),
    re.compile(r'[сc] з[аa]т[pр][аa]т[оo]й [mм][иiеu][нn][иiеu][mм](?:[уy][mм]|[аa]ль[нn][оo]|[аa]ль[нn]ы[mм]) л[иiеu][чч4][нn][оo]г[оo] [вb][pр][еe][mм][еe][нn][иiеu]', re.IGNORECASE),

]

# Порог количества совпадений для удаления сообщения
MATCH_THRESHOLD = 2

# Функция для проверки количества совпадений с рекламными шаблонами
def count_ad_matches(text):
    return sum(1 for pattern in ad_patterns if pattern.search(text))

# Тестовые сообщения
test_messages = [
    "Ищу людей для доп заработка на удаленной основе в свободное время, все подробности в личные сообщения",
    "Работа на дому, гибкий график, подробности в личку",
    "Продаю велосипед, подробности в личные сообщения",
    "Удаленная работа для всех, кто ищет подработку",
    "Подробности в личку о работе на удаленной основе",
    "В поuске людeй, заuнтересованных в пассuвной прuбылu с затpатой мuнuмум лuчного временu.  Все деталu в лс"
]

# Тестирование сообщений
for message in test_messages:
    message = extract_regular_chars(message)
    match_count = count_ad_matches(message)
    if match_count >= MATCH_THRESHOLD:
        print(f"Message: '{message}' is considered advertisement. Matches: {match_count}")
    else:
        print(f"Message: '{message}' is NOT considered advertisement. Matches: {match_count}")
