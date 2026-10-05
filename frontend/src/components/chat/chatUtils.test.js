import { mergeMessages, lastMessageAt } from "./chatUtils";

const msg = (id, minute) => ({ id, created_at: `2026-10-01T00:${String(minute).padStart(2, "0")}:00+00:00` });

describe("mergeMessages", () => {
  it("replaces the list with a full thread response", () => {
    expect(mergeMessages([msg("a", 1)], [msg("b", 2)], false)).toEqual([msg("b", 2)]);
  });

  it("appends new messages from an overlapping incremental poll without duplicates", () => {
    const current = [msg("a", 1), msg("b", 2)];
    const merged = mergeMessages(current, [msg("b", 2), msg("c", 3)], true);
    expect(merged.map((m) => m.id)).toEqual(["a", "b", "c"]);
  });

  it("keeps the same array when an incremental poll has nothing new", () => {
    const current = [msg("a", 1), msg("b", 2)];
    expect(mergeMessages(current, [msg("b", 2)], true)).toBe(current);
    expect(mergeMessages(current, [], true)).toBe(current);
  });

  it("orders a late message by its timestamp", () => {
    const merged = mergeMessages([msg("a", 1), msg("c", 3)], [msg("b", 2)], true);
    expect(merged.map((m) => m.id)).toEqual(["a", "b", "c"]);
    expect(lastMessageAt(merged)).toBe(msg("c", 3).created_at);
    expect(lastMessageAt([])).toBeUndefined();
  });
});
