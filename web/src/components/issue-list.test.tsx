import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { IssueList } from "@/components/issue-list";
import type { IssueDetail } from "@/lib/types";

function issue(overrides: Partial<IssueDetail> = {}): IssueDetail {
  return {
    issue_title: "Missing Projects Section",
    severity_level: "High",
    ats_impact: "High",
    explanation: "No dedicated Projects section was found.",
    where_it_appears: "Resume structure",
    how_to_fix: "Add a Projects section with 2-3 projects.",
    action_items: ["Add a PROJECTS heading", "Include a measurable result"],
    example_improvement: "PROJECTS\nLedger Service — Python, PostgreSQL",
    ...overrides,
  };
}

describe("IssueList", () => {
  it("says so plainly when there are no issues", () => {
    render(<IssueList issues={[]} />);
    expect(screen.getByText(/No issues detected/i)).toBeInTheDocument();
  });

  it("counts the issues and calls out the high-severity ones", () => {
    render(
      <IssueList
        issues={[
          issue({ severity_level: "High" }),
          issue({ issue_title: "Weak verbs", severity_level: "Moderate" }),
        ]}
      />,
    );
    expect(screen.getByText(/2 issues found, 1 high severity/i)).toBeInTheDocument();
  });

  it("uses the singular for one issue", () => {
    render(<IssueList issues={[issue()]} />);
    expect(screen.getByText(/1 issue found/i)).toBeInTheDocument();
  });

  it("orders high severity above moderate and low", () => {
    render(
      <IssueList
        issues={[
          issue({ issue_title: "Low one", severity_level: "Low" }),
          issue({ issue_title: "High one", severity_level: "High" }),
          issue({ issue_title: "Moderate one", severity_level: "Moderate" }),
        ]}
      />,
    );

    const titles = screen
      .getAllByRole("button")
      .map((button) => button.textContent ?? "");

    expect(titles[0]).toContain("High one");
    expect(titles[1]).toContain("Moderate one");
    expect(titles[2]).toContain("Low one");
  });

  it("keeps the detail collapsed until asked", () => {
    render(<IssueList issues={[issue()]} />);

    expect(screen.queryByText(/Add a PROJECTS heading/)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Missing Projects Section/i })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });

  it("reveals the fix and action items when expanded", async () => {
    const user = userEvent.setup();
    render(<IssueList issues={[issue()]} />);

    await user.click(screen.getByRole("button", { name: /Missing Projects Section/i }));

    expect(screen.getByText(/Add a Projects section with 2-3 projects/)).toBeInTheDocument();
    expect(screen.getByText("Add a PROJECTS heading")).toBeInTheDocument();
    expect(screen.getByText(/Ledger Service/)).toBeInTheDocument();
  });

  it("collapses again on a second click", async () => {
    const user = userEvent.setup();
    render(<IssueList issues={[issue()]} />);
    const toggle = screen.getByRole("button", { name: /Missing Projects Section/i });

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");

    await user.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "false");
  });
});
