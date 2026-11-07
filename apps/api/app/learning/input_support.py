"""与原填词键盘一致的稳定候选字符；只在当前学习题目下发。"""

import math
import re

DISTRACTORS = (
    "的一是了不人我在有他这中大来上个国到说们为子和你地出会也时要就可以对生能而着"
    "事前里所去行过家十用发天如然作方成者多日都三小军二无同么经法当起与好看学进种"
    "将还分此心前把把道文些将主实重新明体开它合已从提力此面理由她长角期将再想许让"
    "向又物被全书走给最便位加将些别几义路反条其化或接将片向才助战持区住四带运段切"
    "反确据形今指两打西再至张头走知活步往什"
)


def shuffled(values, seed):
    values = list(values)
    for i in range(len(values) - 1, 0, -1):
        seed = (seed * 16807) % 2147483647
        j = seed % (i + 1)
        values[i], values[j] = values[j], values[i]
    return values


def keyboard(question):
    answer, seed = question["answer"], question["id"]
    english = re.fullmatch(r"[a-zA-Z][a-zA-Z\s'.,!?:;-]*", answer.strip()) is not None
    chars = list(dict.fromkeys(re.sub("[^a-z-]", "", answer.lower()) if english else answer))
    count = max(9, len(chars) + 4) - len(chars)
    if english:
        vowels = shuffled([c for c in "aeiou" if c not in chars], seed + 13)
        consonants = shuffled([c for c in "bcdfghklmnprstwy" if c not in chars], seed + 7)
        distractors = vowels[: min(max(1, math.floor(count / 3 + 0.5)), len(vowels))]
        distractors += consonants[: count - len(distractors)]
    else:
        distractors = shuffled([c for c in DISTRACTORS if c not in chars], seed + 7)[:count]
    return {
        "candidates": shuffled(chars + distractors, seed),
        "language": "letters" if english else "text",
        "max_length": max(10, len(answer.strip())),
    }
