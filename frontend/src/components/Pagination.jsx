export default function Pagination({ page, total, pageSize = 25, onChange, disabled = false }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return <nav className="pagination" aria-label="Pagination">
    <button className="btn btn-outline" disabled={disabled || page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
    <span aria-live="polite">Page {page} of {pages} · {total} results</span>
    <button className="btn btn-outline" disabled={disabled || page >= pages} onClick={() => onChange(page + 1)}>Next</button>
  </nav>;
}
