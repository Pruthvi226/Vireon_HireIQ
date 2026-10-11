import { afterEach, expect, it, vi } from "vitest";
import { downloadBlob } from "./downloads";

afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });

it("starts the browser download and releases its temporary URL after the click", () => {
  vi.useFakeTimers();
  const createObjectURL = vi.fn().mockReturnValue("blob:report");
  const revokeObjectURL = vi.fn();
  vi.stubGlobal("URL", { createObjectURL, revokeObjectURL });
  const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function () {
    expect(this.download).toBe("learning-plan.pdf");
    expect(this.href).toBe("blob:report");
    expect(this.isConnected).toBe(true);
  });
  const blob = new Blob(["%PDF-report"]);
  downloadBlob(blob, "learning-plan.pdf");
  expect(createObjectURL).toHaveBeenCalledWith(blob);
  expect(click).toHaveBeenCalledTimes(1);
  expect(document.querySelector('a[download="learning-plan.pdf"]')).toBeNull();
  expect(revokeObjectURL).not.toHaveBeenCalled();
  vi.advanceTimersByTime(1000);
  expect(revokeObjectURL).toHaveBeenCalledWith("blob:report");
});
