"""与 packages/core/spec/grading-vectors.json 共用显式规则版本。"""

import re
import unicodedata
from fractions import Fraction

GRADING_RULE_VERSION = "cstf-grading-2"
TRUE_VALUES = {"对", "正确", "true", "t", "✓", "√", "y", "yes"}
FALSE_VALUES = {"错", "错误", "false", "f", "✗", "×", "n", "no"}
UNITS = {
    "米": "m",
    "m": "m",
    "厘米": "cm",
    "cm": "cm",
    "毫米": "mm",
    "mm": "mm",
    "分米": "dm",
    "dm": "dm",
    "千米": "km",
    "公里": "km",
    "km": "km",
    "平方米": "m2",
    "m2": "m2",
    "平方厘米": "cm2",
    "cm2": "cm2",
    "平方分米": "dm2",
    "dm2": "dm2",
    "立方米": "m3",
    "m3": "m3",
    "立方厘米": "cm3",
    "cm3": "cm3",
    "升": "l",
    "l": "l",
    "毫升": "ml",
    "ml": "ml",
    "克": "g",
    "g": "g",
    "千克": "kg",
    "公斤": "kg",
    "kg": "kg",
    "吨": "t",
    "t": "t",
    "元": "元",
    "角": "角",
    "分": "分",
    "秒": "秒",
    "秒钟": "秒",
    "分钟": "分钟",
    "小时": "小时",
    "时": "小时",
    "天": "天",
    "个": "个",
    "只": "只",
    "本": "本",
    "支": "支",
    "张": "张",
    "人": "人",
    "次": "次",
    "岁": "岁",
    "度": "度",
    "°": "度",
}
DECIMAL = r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)"
NUMERIC = re.compile(rf"^({DECIMAL})(?:/({DECIMAL}))?(%)?(.*)$")


def width(value):
    return unicodedata.normalize("NFKC", value).replace("−", "-").replace("⁄", "/")


def trim(value):
    return re.sub(r"^[\s\ufeff]+|[\s\ufeff]+$", "", value)


def normalize(value):
    return (
        re.sub(r"[\s\ufeff]+", "", width(value).strip().lower())
        .replace("，", ",")
        .replace("。", ".")
        .replace("：", ":")
    )


def numeric(value):
    value = normalize(value)
    if len(value) > 256:
        return None
    match = NUMERIC.fullmatch(value)
    if not match or (match[4] and match[4] not in UNITS):
        return None
    try:
        number = Fraction(match[1])
        if match[2]:
            number /= Fraction(match[2])
        if match[3]:
            number /= 100
        return number, UNITS.get(match[4], "")
    except (ValueError, ZeroDivisionError):
        return None


def equal_numeric(user, correct):
    u, c = numeric(user), numeric(correct)
    if u is not None and c is not None:
        return not (u[1] and c[1] and u[1] != c[1]) and abs(u[0] - c[0]) < Fraction(1, 1_000_000)
    if u is not None or c is not None:
        return False
    value = normalize(user)
    return (
        not re.fullmatch(r"[+\-0-9./%]+", value)
        and value not in {"nan", "infinity", "+infinity", "-infinity", "∞", "-∞"}
        and value == normalize(correct)
    )


def choice_letter(question):
    correct = trim(width(question["answer"]))
    options = question.get("options", [])
    checks = [
        [trim(width(option)) == correct for option in options],
        [normalize(option) == normalize(correct) for option in options],
        [
            normalize(re.sub(r"^[A-D][.、]\s*", "", width(option), flags=re.I))
            == normalize(correct)
            for option in options
        ],
    ]
    for matches in checks:
        if True in matches:
            return chr(65 + matches.index(True))
    match = re.match(r"^([A-D])(?:$|[.、]\s*)", correct, re.I)
    return match[1].upper() if match and ord(match[1].upper()) - 65 < len(options) else None


def matching(value):
    value = re.sub(r"[\s\ufeff]+", "", width(value).strip().replace("，", ","))
    if not value:
        return None
    result, values = {}, set()
    for pair in value.split(","):
        match = re.fullmatch(r"([a-z]+)-([a-z0-9]+)", pair, re.I)
        if not match:
            return None
        key, right = match[1].upper(), match[2].upper()
        if key in result or right in values:
            return None
        result[key] = right
        values.add(right)
    return result


def grade_answer(question, user_answer):
    if (
        not isinstance(user_answer, str)
        or len(user_answer) > 10000
        or not trim(user_answer)
        or not isinstance(question.get("answer"), str)
    ):
        return False
    correct, kind = question["answer"], question.get("type")
    if kind == "true_false":
        u, c = normalize(user_answer), normalize(correct)

        def boolean(v):
            return True if v in TRUE_VALUES else False if v in FALSE_VALUES else None

        ub, cb = boolean(u), boolean(c)
        return ub == cb if ub is not None and cb is not None else u == c
    if kind == "choice":
        label = choice_letter(question)
        return label is not None and trim(width(user_answer)).upper() == label
    if kind in {"fill_blank", "calculation", "word_problem"}:
        return equal_numeric(user_answer, correct)
    if kind == "fill_blank_text":

        def clean(v):
            return re.sub(r"""[，。！？：；,.!?:;()（）"'`]""", "", normalize(v))

        return clean(user_answer) == clean(correct)
    if kind == "word_order":

        def clean(v):
            return re.sub(r"[\s\ufeff]+", "", width(v).strip().replace("，", ","))

        return clean(user_answer) == clean(correct)
    if kind == "matching":
        u, c = matching(user_answer), matching(correct)
        return u is not None and c is not None and u == c
    return False
