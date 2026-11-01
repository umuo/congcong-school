import { mathSegments } from "@cstf/core/mathSegments";

export function splitMath(text: string) {
  return mathSegments(text).map(({ type, value }) => ({ type, value }));
}
