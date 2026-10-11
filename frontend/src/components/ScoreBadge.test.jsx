import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ScoreBadge from "./ScoreBadge";

describe("ScoreBadge", () => {
  it("clamps and exposes the score accessibly", () => {
    render(<ScoreBadge score={120} />);
    expect(screen.getByLabelText("Match Score: 100%")).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "100%" })).toBeInTheDocument();
  });
});
