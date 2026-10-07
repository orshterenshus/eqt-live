import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./client";

afterEach(() => vi.unstubAllGlobals());

describe("api error handling", () => {
  it("falls back to an HTTP status message when body is not JSON and statusText is empty", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 502,
        statusText: "",
        json: () => Promise.reject(new SyntaxError("not json")),
      }),
    );
    const err = await api.models().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.message).toBe("Request failed (HTTP 502)");
  });

  it("uses the JSON error body when present", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: () => Promise.resolve({ error: "not_found", message: "gone" }),
      }),
    );
    const err = await api.models().catch((e) => e);
    expect(err.code).toBe("not_found");
    expect(err.message).toBe("gone");
  });
});
