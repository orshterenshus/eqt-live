import { describe, expect, it } from "vitest";
import { formatDateline, formatUtcTime, secondsBetween, timeAgo } from "./format";

describe("format", () => {
  it("formats UTC time with hundredths", () => {
    expect(formatUtcTime("2026-10-07T12:00:11.340000Z")).toBe("12:00:11.34");
    expect(formatUtcTime(null)).toBe("—");
  });
  it("computes seconds between timestamps", () => {
    expect(secondsBetween("2026-10-07T12:00:00Z", "2026-10-07T12:00:30.5Z")).toBe(30.5);
  });
  it("describes how long ago", () => {
    const now = Date.parse("2026-10-07T12:00:00Z");
    expect(timeAgo("2026-10-07T11:45:00Z", now)).toBe("15 min ago");
    expect(timeAgo("2026-10-07T07:00:00Z", now)).toBe("5 h ago");
    expect(timeAgo("2026-10-04T12:00:00Z", now)).toBe("3 d ago");
  });
});

describe("formatDateline", () => {
  it("formats a UTC dateline", () => {
    expect(formatDateline(new Date("2026-10-08T14:21:07Z"))).toBe("08 OCT 2026 · 14:21 UTC");
  });
});
