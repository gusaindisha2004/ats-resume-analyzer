import { describe, expect, it } from "vitest";
import { cn, formatDuration, scoreBand } from "@/lib/utils";

describe("scoreBand", () => {
  /** Every colour decision in the UI derives from this, so the thresholds
   *  are worth pinning rather than leaving to a reader of the source. */
  it.each([
    [100, "strong"],
    [80, "strong"],
    [79.9, "fair"],
    [60, "fair"],
    [59.9, "weak"],
    [0, "weak"],
  ])("maps %s to %s", (score, expected) => {
    expect(scoreBand(score)).toBe(expected);
  });

  it("treats the boundaries as inclusive of the better band", () => {
    expect(scoreBand(80)).toBe("strong");
    expect(scoreBand(60)).toBe("fair");
  });
});

describe("formatDuration", () => {
  it("renders months alone under a year", () => {
    expect(formatDuration(7)).toBe("7 mo");
  });

  it("renders whole years without a months part", () => {
    expect(formatDuration(24)).toBe("2 yr");
  });

  it("renders years and months together", () => {
    expect(formatDuration(30)).toBe("2 yr 6 mo");
  });

  it("shows a dash rather than '0 mo' when there is no experience", () => {
    expect(formatDuration(0)).toBe("—");
    expect(formatDuration(-5)).toBe("—");
  });
});

describe("cn", () => {
  it("joins class names", () => {
    expect(cn("a", "b")).toBe("a b");
  });

  it("drops falsey values", () => {
    expect(cn("a", false && "b", undefined, "c")).toBe("a c");
  });

  it("lets a later tailwind class win over an earlier conflicting one", () => {
    // This is the whole reason for tailwind-merge: component defaults must be
    // overridable by a className passed in from the call site.
    expect(cn("px-2", "px-4")).toBe("px-4");
  });
});
