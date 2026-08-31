import React from 'react';

/** Inline **bold** rendering. */
const renderInline = (text: string): React.ReactNode => {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith('**') && p.endsWith('**') ? <strong key={i}>{p.slice(2, -2)}</strong> : <span key={i}>{p}</span>
  );
};

/**
 * Minimal markdown renderer (no dependency) for grounded-research briefs:
 * GitHub-style tables, ### headings, and - / * bullets. Everything else is a
 * paragraph. Good enough to make an LLM markdown brief look clean.
 */
export const MiniMarkdown: React.FC<{ text: string }> = ({ text }) => {
  const lines = text.split('\n');
  const blocks: React.ReactNode[] = [];
  let i = 0;
  let key = 0;

  const isTableRow = (l: string) => l.trim().startsWith('|') && l.includes('|');
  const isDivider = (l: string) => /^\s*\|?[\s:|-]+\|?\s*$/.test(l) && l.includes('-');

  while (i < lines.length) {
    const line = lines[i];

    // Table block
    if (isTableRow(line) && i + 1 < lines.length && isDivider(lines[i + 1])) {
      const cells = (l: string) =>
        l.trim().replace(/^\||\|$/g, '').split('|').map((c) => c.trim());
      const header = cells(line);
      i += 2; // skip header + divider
      const rows: string[][] = [];
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(cells(lines[i]));
        i++;
      }
      blocks.push(
        <div key={key++} style={{ overflowX: 'auto', margin: '8px 0' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: '11.5px' }}>
            <thead>
              <tr>
                {header.map((h, c) => (
                  <th key={c} style={{ textAlign: 'left', padding: '5px 8px', borderBottom: '1px solid var(--line)', background: 'var(--chip)', fontWeight: 650, whiteSpace: 'nowrap' }}>
                    {renderInline(h)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, ri) => (
                <tr key={ri}>
                  {r.map((cell, ci) => (
                    <td key={ci} style={{ padding: '5px 8px', borderBottom: '1px solid var(--line)', verticalAlign: 'top', color: ci === 0 ? 'var(--txt)' : 'var(--muted)' }}>
                      {renderInline(cell)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Heading
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      blocks.push(
        <div key={key++} style={{ fontWeight: 700, fontSize: '13px', margin: '10px 0 4px' }}>
          {renderInline(h[2].replace(/\*\*/g, ''))}
        </div>
      );
      i++;
      continue;
    }

    // Bullet
    const b = line.match(/^\s*[-*]\s+(.*)$/);
    if (b) {
      blocks.push(
        <div key={key++} style={{ display: 'flex', gap: '7px', margin: '2px 0' }}>
          <span style={{ color: 'var(--accent)' }}>•</span>
          <span>{renderInline(b[1])}</span>
        </div>
      );
      i++;
      continue;
    }

    // Blank
    if (!line.trim()) {
      i++;
      continue;
    }

    // Paragraph
    blocks.push(
      <p key={key++} style={{ margin: '4px 0' }}>
        {renderInline(line)}
      </p>
    );
    i++;
  }

  return <div style={{ fontSize: '12.5px', lineHeight: 1.5, color: 'var(--txt)' }}>{blocks}</div>;
};
