export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  try {
    anchor.click();
  } finally {
    anchor.remove();
    // Give the browser time to start reading the object URL before releasing it.
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
