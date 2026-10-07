import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiError } from "../api/client";
import { describeError, ErrorBox } from "./ErrorBox";

describe("ErrorBox", () => {
  it("explains insufficient data in plain words", () => {
    render(<ErrorBox error={new ApiError(422, "insufficient_data", "No waveform data available")} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Try another station");
  });

  it("handles network failures", () => {
    expect(describeError(new TypeError("Failed to fetch"))).toMatch(/could not reach the server/);
  });
});
