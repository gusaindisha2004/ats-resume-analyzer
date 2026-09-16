import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScoreGauge } from "@/components/score-gauge";

describe("ScoreGauge", () => {
  it("shows the rounded score", () => {
    render(<ScoreGauge score={71.4} />);
    expect(screen.getByText("71")).toBeInTheDocument();
  });

  it("announces the score to assistive tech", () => {
    // The number is drawn as SVG; without this the gauge is invisible to a
    // screen reader.
    render(<ScoreGauge score={71} />);
    expect(
      screen.getByRole("img", { name: /ATS Score: 71 out of 100/i }),
    ).toBeInTheDocument();
  });

  it("clamps a score above 100", () => {
    render(<ScoreGauge score={150} />);
    expect(screen.getByText("100")).toBeInTheDocument();
  });

  it("clamps a negative score to zero", () => {
    render(<ScoreGauge score={-20} />);
    expect(screen.getByText("0")).toBeInTheDocument();
  });

  it("accepts a custom label and uses it in the accessible name", () => {
    render(<ScoreGauge score={58} label="JD Match" />);
    expect(screen.getByText("JD Match")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: /JD Match: 58 out of 100/i }),
    ).toBeInTheDocument();
  });

  it("colours the arc by band", () => {
    const { container: strong } = render(<ScoreGauge score={90} />);
    expect(strong.querySelector(".stroke-emerald-500")).toBeTruthy();

    const { container: weak } = render(<ScoreGauge score={30} />);
    expect(weak.querySelector(".stroke-rose-500")).toBeTruthy();
  });
});
