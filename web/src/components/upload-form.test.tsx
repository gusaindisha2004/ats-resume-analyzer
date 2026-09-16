import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

// The real client reaches for a Supabase session and the network.
vi.mock("@/lib/api", () => ({
  analyzeResume: vi.fn(),
  ApiError: class ApiError extends Error {
    constructor(
      message: string,
      readonly status: number,
    ) {
      super(message);
    }
  },
}));

import { analyzeResume, ApiError } from "@/lib/api";
import { UploadForm } from "@/components/upload-form";

const analyze = vi.mocked(analyzeResume);

function file(name: string, sizeBytes = 1024, type = "application/pdf"): File {
  const blob = new Blob(["x".repeat(sizeBytes)], { type });
  return new File([blob], name, { type });
}

async function attach(name: string, size?: number) {
  const user = userEvent.setup();
  const input = document.querySelector('input[type="file"]') as HTMLInputElement;
  await user.upload(input, file(name, size));
  return user;
}

/**
 * Drop a file on the dropzone.
 *
 * The file input carries accept=".pdf,.docx", and both a real file picker and
 * userEvent.upload honour that — an unsupported file can never arrive through
 * it. Drag-and-drop has no such filter, so it is the path by which a .txt or
 * a .doc actually reaches the component, and therefore the path that has to
 * exercise the validation.
 */
function drop(name: string, size?: number) {
  const zone = screen.getByRole("button", { name: /Drop your resume here/i })
    .parentElement as HTMLElement;
  fireEvent.drop(zone, { dataTransfer: { files: [file(name, size)] } });
}

describe("UploadForm", () => {
  beforeEach(() => {
    analyze.mockReset();
  });

  it("disables the submit button until a file is chosen", () => {
    render(<UploadForm onComplete={vi.fn()} />);
    expect(screen.getByRole("button", { name: /Analyze resume/i })).toBeDisabled();
  });

  it("accepts a PDF and enables submission", async () => {
    render(<UploadForm onComplete={vi.fn()} />);
    await attach("resume.pdf");

    expect(screen.getByText("resume.pdf")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Analyze resume/i })).toBeEnabled();
  });

  it("rejects an unsupported extension dropped onto the zone", async () => {
    render(<UploadForm onComplete={vi.fn()} />);
    drop("resume.txt");

    expect(await screen.findByRole("alert")).toHaveTextContent(/PDF or DOCX/i);
    expect(screen.getByRole("button", { name: /Analyze resume/i })).toBeDisabled();
  });

  it("names .doc specifically, since converting it is the fix", async () => {
    render(<UploadForm onComplete={vi.fn()} />);
    drop("resume.doc");

    expect(await screen.findByRole("alert")).toHaveTextContent(/\.doc/i);
  });

  it("accepts a dropped PDF", async () => {
    render(<UploadForm onComplete={vi.fn()} />);
    drop("dropped.pdf");

    expect(await screen.findByText("dropped.pdf")).toBeInTheDocument();
  });

  it("rejects a file over the size limit and reports its size", async () => {
    render(<UploadForm onComplete={vi.fn()} />);
    await attach("huge.pdf", 6 * 1024 * 1024);

    expect(screen.getByRole("alert")).toHaveTextContent(/limit is 5 MB/i);
  });

  it("rejects an empty file", async () => {
    render(<UploadForm onComplete={vi.fn()} />);
    await attach("empty.pdf", 0);

    expect(screen.getByRole("alert")).toHaveTextContent(/empty/i);
  });

  it("submits the file and the job description together", async () => {
    analyze.mockResolvedValue({ ats_score: 71 } as never);
    const onComplete = vi.fn();
    render(<UploadForm onComplete={onComplete} />);

    const user = await attach("resume.pdf");
    await user.type(screen.getByLabelText(/Job description/i), "Python role");
    await user.click(screen.getByRole("button", { name: /Analyze resume/i }));

    await waitFor(() => expect(analyze).toHaveBeenCalledOnce());
    expect(analyze.mock.calls[0][1]).toBe("Python role");
    expect(onComplete).toHaveBeenCalledWith({ ats_score: 71 });
  });

  it("surfaces the backend's own message on failure", async () => {
    analyze.mockRejectedValue(new ApiError("Could not read the resume.", 422));
    render(<UploadForm onComplete={vi.fn()} />);

    const user = await attach("resume.pdf");
    await user.click(screen.getByRole("button", { name: /Analyze resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not read the resume.",
    );
  });

  it("falls back to a connection message for a non-API failure", async () => {
    analyze.mockRejectedValue(new TypeError("fetch failed"));
    render(<UploadForm onComplete={vi.fn()} />);

    const user = await attach("resume.pdf");
    await user.click(screen.getByRole("button", { name: /Analyze resume/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /Could not reach the analysis service/i,
    );
  });

  it("does not call the API when validation already failed", async () => {
    render(<UploadForm onComplete={vi.fn()} />);
    drop("resume.txt");

    await screen.findByRole("alert");
    expect(analyze).not.toHaveBeenCalled();
  });
});
