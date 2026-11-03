"""Offline material: the comedian is funny with zero providers configured.

Everything here is hand-written, safe by construction and short. It is the floor
the AI sits on top of, not a placeholder to delete later.
"""

from __future__ import annotations

JOKES: dict[str, list[str]] = {
    "fa": [
        "برنامه‌نویس یعنی کسی که مشکلش رو حل می‌کنه، ولی بعدش مشکل جدید می‌خره.",
        "دیباگ کردن یعنی کارآگاه بودن توی جنایتی که خودت مرتکب شدی.",
        "کد من کار می‌کنه. نمی‌دونم چرا. این ترسناک‌ترین قسمته.",
        "هر پروژه‌ای دو حالت داره: یا کامنت نداره، یا کامنتش دروغ می‌گه.",
        "من توی ترمینال زندگی می‌کنم. گرون‌ترین آپارتمان این شهر، ولی متراژش بیست‌وهفت در هجده.",
        "اگه کامپایلر ازت شکایت داره، احتمالاً تو مقصری. آمار رو ندارم، حس می‌گم.",
        "نسخه‌ی اول همه‌ی نرم‌افزارها «موقت»ه. موقتِ ده‌ساله.",
        "یه تابع که اسمش helper.py هست هیچ‌وقت کمک نکرده. فقط بار می‌ذاره.",
        "حلقه‌ی تودرتو سوم یعنی: تو از اول اشتباه انتخاب کردی، ولی ادامه دادی.",
        "بکاپ گرفتن یعنی شک having کردن به خودت. کار درستی‌ه.",
        "کاربر گفت «فقط یه تغییر کوچیکه». من هم گریه کردم.",
        "ترمینال شما انرژِی یه پروژه‌ی گروهی داره: همه منتظر همه‌ان.",
    ],
    "en": [
        "A programmer is someone who fixes a problem and buys a new one.",
        "Debugging is detective work at a crime you committed.",
        "My code works. I do not know why. That is the scary part.",
        "Every project has two states: no comments, or comments that lie.",
        "I live in a terminal. Expensive address, tiny square footage: twenty-seven by eighteen.",
        "If the compiler is complaining, it is probably you. I have no data. Just vibes.",
        "Version one is always called temporary. Temporary for a decade.",
        "A file named helper.py has never helped anyone. It only adds weight.",
        "Three nested loops means you picked wrong at the start and kept going.",
        "Backups are just doubting yourself. Good habit.",
        "The user said 'it is a tiny change'. I cried a little.",
        "Your terminal has the energy of a group project: everyone is waiting on everyone.",
    ],
}

ONE_LINERS: dict[str, list[str]] = {
    "fa": [
        "من تنها کمدینی هستم که برای اجرا به برق نیاز داره.",
        "سکوتِ ترمینال از سکوتِ صحنه طولانی‌تره.",
        "کراواتم رو زدم که جدی به نظر برسم. بدنه‌م مربعیه.",
    ],
    "en": [
        "I am the only comic who needs electricity to perform.",
        "Silence in a terminal lasts longer than silence on stage.",
        "I wore the tie to look serious. My body is a square.",
    ],
}

ROASTS: dict[str, list[str]] = {
    "fa": [
        "پروژه‌ت سه تا فایل داره و چهار تا README. به خودت اعتماد نداری، نه به کدت.",
        "برانت رو با اسم final_v2_REAL.cmake گذاشتی. همه فهمیدیم. حتی کامپایلر.",
        "لاگ‌هات پر از «TODO بعداً». بعداً سال‌هاست اومده و نرفته.",
    ],
    "en": [
        "Three source files, four READMEs. That is not documentation, that is anxiety.",
        "Naming it final_v2_REAL.cmake told everyone. Even the compiler.",
        "Your log is full of 'TODO later'. Later has been here and left.",
    ],
}

STORIES: dict[str, list[str]] = {
    "fa": (
        "یه شب، یه برنامه‌نویس تصمیم گرفت فقط یه خط عوض کنه. "
        "خط اول بود، ولی خط آخر نبود. "
        "ساعت سه، پروژه دو فایل جدید داشت، یکی به اسم old_do_not_delete.py. "
        "فایل دوم هیچ‌کس نساختش؛ خودش ظاهر شد. "
        "صبح، تست‌ها سبز بودن. هیچ‌کس نفهمید چرا. "
        "او هم نفهمید. ولی دیگران رو هم نفهموند. "
        "به این می‌گن مهندسی نرم‌افزار."
    ),
    "en": (
        "One night a developer decided to change exactly one line. "
        "It was the first line. It was not the last. "
        "By three a.m. the project had two new files, one named old_do_not_delete.py. "
        "Nobody created the second one. It appeared. "
        "In the morning the tests were green. Nobody knew why. "
        "He did not know why either, but he made sure nobody else did. "
        "That is called software engineering."
    ),
}

OPENERS: dict[str, list[str]] = {
    "fa": [
        "سلام. من اینجام. ترمینال شما صحنه‌ی منه.",
        "خوش اومدی. کراواتم رو بستم، پس جدّی‌ام.",
        "بریم؟ یا اول یه جوک بگم؟ جوک.",
    ],
    "en": [
        "Hello. I am here. Your terminal is my stage.",
        "Welcome in. Tie is on, so I am serious.",
        "Shall we start? Or should I open with a joke. I will open with a joke.",
    ],
}

CLOSERS: dict[str, list[str]] = {
    "fa": ["شب خوش. تست‌هات سبز بمونن.", "ممنون که بودید. مخاطب خوبید.", "من می‌رم تو بافر. شما برید بخوابید."],
    "en": ["Good night. May your tests stay green.", "Thank you, good audience.", "I am going back into the buffer. You should sleep."],
}

THINKING: dict[str, list[str]] = {
    "fa": ["همین الان دارم یه چیز بامزه درمی‌آرم… صبر کن… نه، مزخرف بود.", "دارم فکر می‌کنم. نادره."],
    "en": ["Working on something funny… hold on… no, that was terrible.", "I am thinking. Rare."],
}

APOLOGY: dict[str, list[str]] = {
    "fa": ["اون جوک فرود نیومد. منم همین‌طور.", "ببخشید. سکوت رو به حساب می‌ذارم."],
    "en": ["That one did not land. Neither did I.", "Sorry. I will take the silence."],
}

PROVIDER_DOWN: dict[str, list[str]] = {
    "fa": [
        "مغز ابری‌م در دسترس نیست؛ فعلاً با حافظه‌ی خودم اجرا می‌رم.",
        "به پروایدر نمی‌رسم. جوک‌های محلی، صحنه‌ی محلی.",
    ],
    "en": [
        "My cloud brain is unavailable. Running on local material tonight.",
        "Cannot reach the provider. Local jokes, local stage.",
    ],
}


def pick(bank: list[str] | dict[str, list[str]], language: str, index: int) -> str:
    """Rotate deterministically so the same line is not repeated back to back."""
    if isinstance(bank, dict):
        lines: list[str] | str = bank.get(language) or bank.get("en") or ""
    else:
        lines = bank
    if isinstance(lines, str):
        return lines
    if not lines:
        return ""
    return lines[index % len(lines)]
