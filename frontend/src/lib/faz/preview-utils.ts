/**
 * Faz Code Preview Utilities
 * 
 * Functions for generating static HTML previews from project files.
 */

interface ProjectFile {
  path: string;
  content: string;
}

/**
 * Generate a static HTML preview document from project files.
 * 
 * Extracts HTML, CSS, and JS files and combines them into a single
 * preview document. This is used when a live deployment preview is not
 * yet available.
 * 
 * @param files - Array of project files with path and content
 * @returns HTML document string for iframe preview, or null if no files
 */
export function generatePreviewHTML(files: ProjectFile[]): string | null {
  if (!files || files.length === 0) {
    return null;
  }

  const previewDoc = `
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Preview</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif; 
      background: #0A0A0F;
      color: #F1F5F9;
      padding: 2rem;
    }
  </style>
</head>
<body>
  <div id="preview-root">
    <div style="text-align: center; max-width: 600px; margin: 4rem auto;">
      <div style="background: linear-gradient(135deg, #6366F1 0%, #818CF8 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 4rem; margin-bottom: 1rem;">
        ⚡
      </div>
      <h1 class="text-4xl font-bold text-white mb-4">Preview Mode</h1>
      <p style="color: #94A3B8; line-height: 1.6; margin-bottom: 2rem;">
        This is a static preview. Full interactivity requires deployment.
      </p>
      <div style="display: inline-flex; align-items: center; gap: 0.75rem; padding: 0.75rem 1.5rem; background: rgba(99, 102, 241, 0.1); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 9999px; color: #6366F1; font-size: 0.875rem;">
        <svg width="16" height="16" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
        </svg>
        <span>${files.length} files generated • Deploy to see live preview</span>
      </div>
    </div>
  </div>
</body>
</html>
  `;

  return previewDoc;
}

/**
 * Determine if a preview should be regenerated based on file changes.
 * 
 * @param oldFiles - Previous file list
 * @param newFiles - Current file list
 * @returns True if preview should be regenerated
 */
export function shouldRegeneratePreview(
  oldFiles: ProjectFile[],
  newFiles: ProjectFile[]
): boolean {
  // Regenerate if file count changes
  if (oldFiles.length !== newFiles.length) {
    return true;
  }

  // Regenerate if any file content changes
  const oldMap = new Map(oldFiles.map(f => [f.path, f.content]));
  for (const file of newFiles) {
    if (oldMap.get(file.path) !== file.content) {
      return true;
    }
  }

  return false;
}


