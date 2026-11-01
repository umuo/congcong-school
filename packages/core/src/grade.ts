/** 显式版本判分；只影响新作答，不重新计算旧完成记录。 */
import type { Question } from "./types";

export const GRADING_RULE_VERSION = "cstf-grading-2";
const TRUE_VALUES = new Set(["对", "正确", "true", "t", "✓", "√", "y", "yes"]);
const FALSE_VALUES = new Set(["错", "错误", "false", "f", "✗", "×", "n", "no"]);
const UNITS: Record<string, string> = {
  米: "m",
  m: "m",
  厘米: "cm",
  cm: "cm",
  毫米: "mm",
  mm: "mm",
  分米: "dm",
  dm: "dm",
  千米: "km",
  公里: "km",
  km: "km",
  平方米: "m2",
  m2: "m2",
  平方厘米: "cm2",
  cm2: "cm2",
  平方分米: "dm2",
  dm2: "dm2",
  立方米: "m3",
  m3: "m3",
  立方厘米: "cm3",
  cm3: "cm3",
  升: "l",
  l: "l",
  毫升: "ml",
  ml: "ml",
  克: "g",
  g: "g",
  千克: "kg",
  公斤: "kg",
  kg: "kg",
  吨: "t",
  t: "t",
  元: "元",
  角: "角",
  分: "分",
  秒: "秒",
  秒钟: "秒",
  分钟: "分钟",
  小时: "小时",
  时: "小时",
  天: "天",
  个: "个",
  只: "只",
  本: "本",
  支: "支",
  张: "张",
  人: "人",
  次: "次",
  岁: "岁",
  度: "度",
  "°": "度",
};
const DECIMAL = "[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)";
const NUMERIC = new RegExp(`^(${DECIMAL})(?:/(${DECIMAL}))?(%)?(.*)$`);
function trim(s: string): string {
  return s.replace(/^[\s\u0085\u001c-\u001f]+|[\s\u0085\u001c-\u001f]+$/g, "");
}
function width(s: string): string {
  return s.normalize("NFKC").replace(/−/g, "-").replace(/⁄/g, "/");
}
function normalize(s: string): string {
  return trim(width(s))
    .toLowerCase()
    .replace(/[\s\u0085\u001c-\u001f]+/g, "")
    .replace(/，/g, ",")
    .replace(/。/g, ".")
    .replace(/：/g, ":");
}
function decimal(raw: string): [bigint, bigint] {
  const negative = raw.startsWith("-");
  const [whole, fraction = ""] = raw.replace(/^[+-]/, "").split(".");
  return [
    BigInt((whole || "0") + fraction) * (negative ? -1n : 1n),
    10n ** BigInt(fraction.length),
  ];
}
function numeric(raw: string): { n: bigint; d: bigint; unit: string } | null {
  const text = normalize(raw);
  if (text.length > 256) return null;
  const match = text.match(NUMERIC);
  if (!match) return null;
  const suffix = match[4] ?? "";
  if (suffix && !Object.prototype.hasOwnProperty.call(UNITS, suffix))
    return null;
  let [n, d] = decimal(match[1]);
  if (match[2]) {
    const [divisor, scale] = decimal(match[2]);
    if (divisor === 0n) return null;
    n *= scale;
    d *= divisor;
  }
  if (match[3]) d *= 100n;
  if (d < 0n) {
    n = -n;
    d = -d;
  }
  return { n, d, unit: suffix ? UNITS[suffix] : "" };
}
function equalNumeric(user: string, correct: string): boolean {
  const u = numeric(user),
    c = numeric(correct);
  if (u && c) {
    if (u.unit && c.unit && u.unit !== c.unit) return false;
    const delta = u.n * c.d - c.n * u.d;
    return (delta < 0n ? -delta : delta) * 1000000n < u.d * c.d;
  }
  if (u || c) return false;
  // 非数值型原答案（如完整算式、中文回答）仍按规范化文本比较。
  const value = normalize(user);
  return (
    !/^[+\-0-9./%]+$/.test(value) &&
    !["nan", "infinity", "+infinity", "-infinity", "∞", "-∞"].includes(value) &&
    value === normalize(correct)
  );
}

/** 先解析完整选项语义，再回退到明确的位置字母，不能截取答案首字符。 */
export function correctChoiceLetter(
  question: Pick<Question, "answer" | "options">,
): string | null {
  const correct = trim(width(question.answer)),
    options = question.options ?? [];
  const strip = (text: string) => width(text).replace(/^[A-D][.、]\s*/i, "");
  let index = options.findIndex((option) => trim(width(option)) === correct);
  if (index < 0)
    index = options.findIndex(
      (option) => normalize(option) === normalize(correct),
    );
  if (index < 0)
    index = options.findIndex(
      (option) => normalize(strip(option)) === normalize(correct),
    );
  if (index >= 0) return String.fromCharCode(65 + index);
  const label =
    correct.match(/^([A-D])(?:$|[.、]\s*)/i)?.[1].toUpperCase() ?? null;
  return label && label.charCodeAt(0) - 65 < options.length ? label : null;
}
function matching(s: string): Map<string, string> | null {
  const value = width(s)
    .trim()
    .replace(/，/g, ",")
    .replace(/[\s\u0085\u001c-\u001f]+/g, "");
  if (!value) return null;
  const result = new Map<string, string>(),
    values = new Set<string>();
  for (const pair of value.split(",")) {
    const match = pair.match(/^([a-z]+)-([a-z0-9]+)$/i);
    if (!match) return null;
    const key = match[1].toUpperCase(),
      right = match[2].toUpperCase();
    if (result.has(key) || values.has(right)) return null;
    result.set(key, right);
    values.add(right);
  }
  return result;
}
export function gradeAnswer(question: Question, userAnswer: string): boolean {
  if (
    typeof userAnswer !== "string" ||
    userAnswer.length > 10000 ||
    !trim(userAnswer) ||
    typeof question.answer !== "string"
  )
    return false;
  const correct = question.answer;
  switch (question.type) {
    case "true_false": {
      const u = normalize(userAnswer),
        c = normalize(correct);
      const bool = (v: string) =>
        TRUE_VALUES.has(v) ? true : FALSE_VALUES.has(v) ? false : null;
      const ub = bool(u),
        cb = bool(c);
      return ub !== null && cb !== null ? ub === cb : u === c;
    }
    case "choice": {
      const label = correctChoiceLetter(question);
      return label !== null && trim(width(userAnswer)).toUpperCase() === label;
    }
    case "fill_blank":
    case "calculation":
    case "word_problem":
      return equalNumeric(userAnswer, correct);
    case "fill_blank_text": {
      const clean = (s: string) =>
        normalize(s).replace(/[，。！？：；,.!?:;()（）"'`]/g, "");
      return clean(userAnswer) === clean(correct);
    }
    case "word_order": {
      const clean = (s: string) =>
        width(s)
          .trim()
          .replace(/，/g, ",")
          .replace(/[\s\u0085\u001c-\u001f]+/g, "");
      return clean(userAnswer) === clean(correct);
    }
    case "matching": {
      const u = matching(userAnswer),
        c = matching(correct);
      if (!u || !c || u.size !== c.size) return false;
      return [...u].every(([key, value]) => c.get(key) === value);
    }
    default:
      return false;
  }
}
