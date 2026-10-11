import { useEffect, useState } from "react";
import { api } from "../api";

const megabytes = (bytes) => `${Number((bytes / (1024 * 1024)).toFixed(1))} MB`;

export default function BulkResumeImport({ disabled = false, onImported, onBusyChange }) {
  const [limits, setLimits] = useState(null);
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [retry, setRetry] = useState(0);

  useEffect(() => {
    let active = true;
    setError("");
    api.resumeLimits().then((value) => { if (active) setLimits(value); })
      .catch((err) => { if (active) setError(`Import unavailable: ${err.message}`); });
    return () => { active = false; };
  }, [retry]);

  function chooseFiles(event) {
    const selection = Array.from(event.target.files || []);
    event.target.value = "";
    setResults(null); setError(""); setFiles([]);
    if (!selection.length) return;
    const extensions = [...limits.extensions, limits.archive_extension];
    if (selection.length > limits.max_bulk_files) {
      setError(`Choose no more than ${limits.max_bulk_files} files.`); return;
    }
    if (selection.some((file) => !extensions.some((extension) => file.name.toLowerCase().endsWith(extension)))) {
      setError("Choose TXT, PDF, DOCX or ZIP files."); return;
    }
    const oversized = selection.find((file) => !file.name.toLowerCase().endsWith(limits.archive_extension) && file.size > limits.max_resume_bytes);
    if (oversized) {
      setError(`${oversized.name} exceeds the ${megabytes(limits.max_resume_bytes)} document limit.`); return;
    }
    if (selection.reduce((total, file) => total + file.size, 0) > limits.max_bulk_bytes) {
      setError(`The selected batch exceeds ${megabytes(limits.max_bulk_bytes)}.`); return;
    }
    setFiles(selection);
  }

  async function importFiles(event) {
    event.preventDefault();
    if (!files.length || busy || disabled) return;
    setBusy(true); onBusyChange?.(true); setError(""); setResults(null);
    try {
      const form = new FormData();
      files.forEach((file) => form.append("files", file));
      const outcome = await api.bulkUploadResumes(form);
      setResults(outcome); setFiles([]);
      if (outcome.succeeded > 0) {
        try { await onImported?.(); }
        catch { setError("Imports were saved, but the candidate list could not refresh. Reload the page before importing again."); }
      }
    } catch (err) {
      setError(`${err.message}. Some documents may already be saved. Refresh the candidate list before retrying to avoid duplicates.`);
      setFiles([]);
    } finally {
      setBusy(false); onBusyChange?.(false);
    }
  }

  return <section className="page-stack" aria-labelledby="bulk-import-title">
    <h3 id="bulk-import-title">Import a resume batch</h3>
    <p className="muted">Choose multiple documents or a ZIP archive. PDFs need selectable text.</p>
    {limits && <p className="muted">Up to {limits.max_bulk_files} resumes, {megabytes(limits.max_resume_bytes)} per document and {megabytes(limits.max_bulk_bytes)} per batch. ZIP contents share these limits.</p>}
    {!limits && !error && <p role="status">Checking upload limits…</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
    {!limits && error && <button type="button" className="btn btn-outline" onClick={() => setRetry((value) => value + 1)}>Retry upload limits</button>}
    <form className="page-stack" onSubmit={importFiles}>
      <label>Batch resume files<input type="file" accept=".txt,.pdf,.docx,.zip" multiple disabled={!limits || busy || disabled} onChange={chooseFiles} /></label>
      {files.length > 0 && <ul className="content-list">{files.map((file, index) => <li key={`${file.name}-${index}`}>{file.name} · {megabytes(file.size)}</li>)}</ul>}
      <button className="btn btn-primary" disabled={!limits || !files.length || busy || disabled}>{busy ? "Importing resumes…" : `Import ${files.length || "selected"} ${files.length === 1 ? "resume" : "resumes"}`}</button>
    </form>
    {results && <>
      <p role="status">{results.succeeded} imported; {results.failed} failed.</p>
      <ul className="content-list" aria-label="Batch import results">{results.results.map((item, index) => <li key={`${item.filename}-${index}`}>
        <strong>{item.filename}</strong>: {item.status === "success" ? `Imported${item.candidate?.name ? ` — ${item.candidate.name}` : ""}` : `Failed — ${item.error}`}
      </li>)}</ul>
      {results.failed > 0 && <p className="muted">Successful imports are saved. Correct and select only failed documents to retry; reimporting a whole archive may duplicate successful entries.</p>}
    </>}
  </section>;
}
