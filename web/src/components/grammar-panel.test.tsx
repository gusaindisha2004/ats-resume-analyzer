import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GrammarPanel } from "@/components/grammar-panel";
import type { GrammarReport } from "@/lib/types";

const EMPTY: GrammarReport = {
  total_errors: 0,
  score: 100,
  critical: [],
  moderate: [],
  minor: [],
};

describe("GrammarPanel", () => {
  it("reports a clean document and explains what was excluded", () => {
    render(<GrammarPanel data={EMPTY} />);

    expect(screen.getByText(/no issues/i)).toBeInTheDocument();
    // Saying what was skipped is what stops a clean result reading as a
    // check that simply didn't run.
    expect(
      screen.getByText(/Technology names and\s+British spellings are excluded/i),
    ).toBeInTheDocument();
  });

  it("shows the misspelling alongside its correction", () => {
    render(
      <GrammarPanel
        data={{
          ...EMPTY,
          total_errors: 1,
          score: 85,
          critical: [
            {
              error_text: "developement",
              message: "'developement' looks misspelled.",
              suggestions: ["development"],
              context: "Responsible for the backend developement",
            },
          ],
        }}
      />,
    );

    expect(screen.getByText("developement")).toBeInTheDocument();
    expect(screen.getByText("development")).toBeInTheDocument();
    expect(screen.getByText(/Responsible for the backend/)).toBeInTheDocument();
  });

  it("separates spelling from writing style", () => {
    render(
      <GrammarPanel
        data={{
          ...EMPTY,
          total_errors: 2,
          score: 78,
          critical: [
            { error_text: "sytem", message: "misspelled", suggestions: ["system"], context: "" },
          ],
          moderate: [
            { error_text: "I", message: "Avoid first-person pronouns", suggestions: [], context: "" },
          ],
        }}
      />,
    );

    expect(screen.getByText(/Spelling \(1\)/i)).toBeInTheDocument();
    expect(screen.getByText(/Writing style \(1\)/i)).toBeInTheDocument();
  });

  it("omits a severity group that has no findings", () => {
    render(
      <GrammarPanel
        data={{
          ...EMPTY,
          total_errors: 1,
          critical: [
            { error_text: "sytem", message: "misspelled", suggestions: [], context: "" },
          ],
        }}
      />,
    );

    expect(screen.queryByText(/Writing style/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/Polish/i)).not.toBeInTheDocument();
  });

  it("pluralises the issue count", () => {
    render(
      <GrammarPanel
        data={{
          ...EMPTY,
          total_errors: 3,
          minor: [
            { error_text: "a", message: "m", suggestions: [], context: "" },
            { error_text: "b", message: "m", suggestions: [], context: "" },
            { error_text: "c", message: "m", suggestions: [], context: "" },
          ],
        }}
      />,
    );

    expect(screen.getByText("3 issues")).toBeInTheDocument();
  });
});
