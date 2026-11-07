import { playSfx } from "../sfx";
const handled = new WeakSet<Event>();
/** A native intent is handled once, even if a containing shell also receives it. */
export function clickFeedback(event: Event, target: Element, hidden: boolean, play: () => void = () => playSfx("tap", { volume: .45 })) {
  if (handled.has(event) || hidden) return;
  const control = target.closest("button,a,input,select,summary");
  if (!control || control.matches(":disabled,[aria-disabled=true]") || control.closest("[data-silent],[data-sound-handled]")) return;
  handled.add(event);
  try { play(); } catch { /* Optional feedback must never prevent the action. */ }
}
