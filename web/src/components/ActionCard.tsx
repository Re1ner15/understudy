import React from 'react';
import { LiveAction, ActionCategory } from '../data/types';
import { StatusPill } from './StatusPill';
import { Avatar } from './Avatar';
import { approveAction, editAction, skipAction } from '../data';
import { MiniMarkdown } from './MiniMarkdown';

interface ActionCardProps {
  action: LiveAction;
}

const getCategoryIcon = (category: ActionCategory) => {
  switch (category) {
    case 'email':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '16px', height: '16px' }}>
          <rect x="3" y="5" width="18" height="14" rx="2" />
          <path d="m3 7 9 6 9-6" />
        </svg>
      );
    case 'doc':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '16px', height: '16px' }}>
          <path d="M6 2h9l5 5v15H6z" />
          <path d="M14 2v6h6M9 13h7M9 17h7" />
        </svg>
      );
    case 'calendar':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '16px', height: '16px' }}>
          <rect x="3" y="4" width="18" height="17" rx="2" />
          <path d="M3 9h18M8 2v4M16 2v4" />
        </svg>
      );
    case 'research':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ width: '16px', height: '16px' }}>
          <circle cx="11" cy="11" r="7" />
          <path d="M16.5 16.5L21 21" />
        </svg>
      );
    case 'slack':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '16px', height: '16px' }}>
          <path d="M4 4h16v12H8l-4 4z" />
        </svg>
      );
    case 'task':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '16px', height: '16px' }}>
          <path d="M9 11l3 3L22 4" />
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
        </svg>
      );
    case 'code':
      return (
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" style={{ width: '16px', height: '16px' }}>
          <circle cx="6" cy="6" r="2.4" />
          <circle cx="6" cy="18" r="2.4" />
          <circle cx="18" cy="9" r="2.4" />
          <path d="M6 8.4v7.2M18 11.4c0 3-3 3.6-6 3.6" />
        </svg>
      );
  }
};

/** Parses a code action's artifact into structured GitHub detail. */
const parseCode = (artifact?: string | null) => {
  if (!artifact) return null;
  const issue = artifact.match(/Issue:\s*#(\d+)\s+(\S+)/);
  const pr = artifact.match(/PR:\s*#(\d+)\s+(\S+)/);
  const repo = artifact.match(/Repo:\s*(\S+)/);
  const file = artifact.match(/File:\s*(\S+)/);
  const branch = artifact.match(/Branch:\s*(\S+)/);
  // Everything after the metadata block (first blank line following "Branch:")
  const rest = artifact.match(/Branch:\s*\S+\s*\n\s*\n([\s\S]*)$/);
  let prTitle = '';
  let prBody = '';
  let diff = '';
  if (rest) {
    const [meta, diffPart] = rest[1].split('===DIFF===');
    diff = (diffPart || '').trim();
    const lines = meta.trim().split('\n');
    prTitle = lines[0] || '';
    prBody = lines.slice(1).join('\n').trim();
  }
  if (!issue && !pr) return null;
  return {
    issue: issue ? { num: issue[1], url: issue[2] } : null,
    pr: pr ? { num: pr[1], url: pr[2] } : null,
    repo: repo ? repo[1] : null,
    file: file ? file[1] : null,
    branch: branch ? branch[1] : null,
    prTitle,
    prBody,
    diff,
  };
};

/** Colors a unified-diff line for inline review. */
const diffLineStyle = (line: string): React.CSSProperties => {
  const base: React.CSSProperties = {
    display: 'block',
    whiteSpace: 'pre',
    padding: '0 8px',
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
    fontSize: '11.5px',
    lineHeight: 1.55,
  };
  if (line.startsWith('+') && !line.startsWith('+++'))
    return { ...base, background: 'rgba(22,163,74,0.14)', color: '#15803d' };
  if (line.startsWith('-') && !line.startsWith('---'))
    return { ...base, background: 'rgba(239,68,68,0.13)', color: '#b91c1c' };
  if (line.startsWith('@@')) return { ...base, color: '#7c6bd6' };
  if (line.startsWith('+++') || line.startsWith('---'))
    return { ...base, color: 'var(--faint)' };
  return { ...base, color: 'var(--muted)' };
};

// Per-category color: a vibrant-ish tint + a solid accent bar so each action
// type reads at a glance.
const CATEGORY_COLORS: Record<string, { bg: string; bar: string; chip: string }> = {
  email: { bg: 'rgba(59,130,246,0.16)', bar: '#3b82f6', chip: 'rgba(59,130,246,0.22)' },
  research: { bg: 'rgba(139,92,246,0.16)', bar: '#8b5cf6', chip: 'rgba(139,92,246,0.22)' },
  doc: { bg: 'rgba(14,165,233,0.15)', bar: '#0ea5e9', chip: 'rgba(14,165,233,0.22)' },
  calendar: { bg: 'rgba(245,158,11,0.18)', bar: '#f59e0b', chip: 'rgba(245,158,11,0.24)' },
  slack: { bg: 'rgba(217,70,160,0.15)', bar: '#d946a0', chip: 'rgba(217,70,160,0.22)' },
  task: { bg: 'rgba(100,116,139,0.16)', bar: '#64748b', chip: 'rgba(100,116,139,0.22)' },
  code: { bg: 'rgba(16,185,129,0.17)', bar: '#10b981', chip: 'rgba(16,185,129,0.24)' },
};

export const ActionCard: React.FC<ActionCardProps> = ({ action }) => {
  const isPending = action.status === 'needs_approval';
  const c = CATEGORY_COLORS[action.category] || { bg: 'var(--panel)', bar: 'var(--line)', chip: 'var(--chip)' };

  const getSubMeta = () => {
    if (action.assignee) {
      if (action.status === 'needs_approval') return `${action.assignee} · due today`;
      if (action.status === 'running') return `${action.assignee} · drafting…`;
      if (action.status === 'done') {
        if (action.category === 'calendar') return `${action.assignee} · invite sent`;
        if (action.category === 'research') return `${action.assignee} · brief ready`;
        return `${action.assignee} · completed`;
      }
      return `${action.assignee}`;
    }
    return action.status === 'queued' ? 'queued' : 'unassigned';
  };

  return (
    <div
      className={`card ${isPending ? 'pending' : ''}`}
      style={{
        background: c.bg,
        border: '1px solid var(--line)',
        borderLeft: `4px solid ${c.bar}`,
        borderRadius: '13px',
        padding: '14px 15px',
        boxShadow: 'var(--card-sh)',
      }}
    >
      <div className="crow" style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
        <div
          className="ico"
          style={{
            width: '32px',
            height: '32px',
            borderRadius: '9px',
            flex: 'none',
            display: 'grid',
            placeItems: 'center',
            background: c.chip,
            border: `1px solid ${c.bar}`,
            color: c.bar,
          }}
        >
          {getCategoryIcon(action.category)}
        </div>

        <div className="cmain" style={{ flex: 1, minWidth: 0 }}>
          <div className="ttl" style={{ fontWeight: 600, lineHeight: 1.35, marginBottom: '5px' }}>
            {action.title}
          </div>
          <div className="meta" style={{ display: 'flex', alignItems: 'center', gap: '9px', color: 'var(--faint)', fontSize: '12px' }}>
            <Avatar name={action.assignee} size="sm" />
            <span>{getSubMeta()}</span>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 'none' }}>
          {isPending && (
            <span
              title="Needs your approval"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
                background: 'var(--amber-bg, #fdf1d8)',
                color: 'var(--amber-bd, #b7791f)',
                border: '1px solid var(--amber-bd, #e3b877)',
                borderRadius: '999px',
                padding: '3px 8px',
                fontSize: '11px',
                fontWeight: 700,
                whiteSpace: 'nowrap',
              }}
            >
              <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                <path d="M4 2a1 1 0 0 1 1 1v.35l1.4-.35A6 6 0 0 1 12 3.6l.9.45a4 4 0 0 0 3.4.2L19 3.3A1 1 0 0 1 20.5 4.2v9a1 1 0 0 1-.6.92l-3 1.3a6 6 0 0 1-5-.3l-.9-.45a4 4 0 0 0-3.4-.2L5 15v6a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1z" />
              </svg>
              Needs you
            </span>
          )}
          <StatusPill status={action.status} />
        </div>
      </div>

      {action.reasoning && (
        <div
          className="why"
          style={{
            fontSize: '12.5px',
            color: 'var(--muted)',
            lineHeight: 1.45,
            marginTop: '10px',
            paddingLeft: '11px',
            borderLeft: '2px solid var(--accent-soft2)',
          }}
        >
          {action.reasoning.startsWith('Heard') || action.reasoning.startsWith('Extracted') || action.reasoning.startsWith('Committed') ? (
            <>
              <b>Why: </b>
              {action.reasoning}
            </>
          ) : (
            action.reasoning
          )}
        </div>
      )}

      {action.relatedMemory && action.relatedMemory.length > 0 && (
        <div
          style={{
            marginTop: '9px',
            padding: '8px 11px',
            background: 'rgba(124,107,214,0.08)',
            border: '1px solid rgba(124,107,214,0.25)',
            borderRadius: '9px',
          }}
        >
          {action.relatedMemory.map((m, i) => {
            const label =
              m.kind === 'email' ? '📧 From an email'
              : m.kind === 'transcript' ? '📄 From a past transcript'
              : '↩ Recalled';
            return (
              <div key={i} style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: 1.5, marginTop: i ? '4px' : 0 }}>
                <span style={{ color: '#7c6bd6', fontWeight: 700 }}>{label}</span> — {m.text}
                <span style={{ color: 'var(--faint)' }}> · {m.meetingTitle}, {m.date}</span>
              </div>
            );
          })}
        </div>
      )}

      {action.category === 'code' && (() => {
        const c = parseCode(action.artifact);
        if (!c) return null;
        const chip = {
          display: 'inline-flex', alignItems: 'center', gap: '5px',
          fontSize: '11.5px', fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
          padding: '3px 8px', borderRadius: '6px',
          background: 'var(--chip)', border: '1px solid var(--line)', color: 'var(--muted)',
        } as const;
        return (
          <div
            className="code-detail"
            style={{
              marginTop: '11px',
              border: '1px solid var(--line)',
              borderRadius: '10px',
              overflow: 'hidden',
              background: 'var(--panel, #fff)',
            }}
          >
            {/* metadata row */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '7px', padding: '10px 12px', borderBottom: '1px solid var(--line)' }}>
              {c.repo && <span style={chip}>📦 {c.repo}</span>}
              {c.file && <span style={chip}>📄 {c.file}</span>}
              {c.branch && <span style={chip}>⑂ {c.branch}</span>}
            </div>
            {/* PR title + change description */}
            <div style={{ padding: '10px 12px' }}>
              {c.prTitle && (
                <div style={{ fontWeight: 650, fontSize: '13px', marginBottom: '5px' }}>{c.prTitle}</div>
              )}
              {c.prBody && (
                <div style={{ fontSize: '12.5px', color: 'var(--muted)', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                  {c.prBody}
                </div>
              )}
            </div>
            {/* actual code diff for review */}
            {c.diff && (
              <div style={{ borderTop: '1px solid var(--line)' }}>
                <div style={{ padding: '7px 12px', fontSize: '11px', fontWeight: 650, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--faint)' }}>
                  Proposed diff — {c.file}
                </div>
                <div style={{ maxHeight: '260px', overflow: 'auto', paddingBottom: '6px', background: 'var(--chip)' }}>
                  {c.diff.split('\n').map((ln, i) => (
                    <span key={i} style={diffLineStyle(ln)}>{ln || ' '}</span>
                  ))}
                </div>
              </div>
            )}
            {/* links */}
            <div style={{ display: 'flex', gap: '16px', padding: '10px 12px', borderTop: '1px solid var(--line)', fontSize: '12.5px' }}>
              {c.issue && (
                <a href={c.issue.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>
                  Issue #{c.issue.num} →
                </a>
              )}
              {c.pr && (
                <a href={c.pr.url} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600 }}>
                  {action.status === 'done' ? `PR #${c.pr.num} (ready) →` : `Draft PR #${c.pr.num} →`}
                </a>
              )}
            </div>
          </div>
        );
      })()}

      {action.category === 'research' && action.artifact && (() => {
        const [findingsRaw, srcPart] = action.artifact.split('===SOURCES===');
        let findings = (findingsRaw || '').trim();
        const sources = (srcPart || '')
          .trim()
          .split('\n')
          .map((l) => {
            const [title, url] = l.split(' | ');
            return { title: (title || '').trim(), url: (url || '').trim() };
          })
          .filter((s) => s.url);
        if (!findings) return null;

        // Pull the TL;DR out of the findings so we can feature it as a callout.
        let tldr = '';
        const tldrMatch = findings.match(/\*\*TL;DR:?\*\*\s*(.+?)(?:\n|$)/i) || findings.match(/TL;DR:?\s*(.+?)(?:\n|$)/i);
        if (tldrMatch) {
          tldr = tldrMatch[1].trim();
          findings = findings.replace(tldrMatch[0], '').trim();
        }
        const domain = (u: string) => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return u; } };

        return (
          <div style={{ marginTop: '11px', border: '1px solid var(--line)', borderRadius: '10px', overflow: 'hidden', background: 'var(--panel, #fff)' }}>
            {/* Header banner */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '9px 13px', borderBottom: '1px solid var(--line)', background: 'rgba(139,92,246,0.10)' }}>
              <span style={{ fontSize: '13px' }}>📊</span>
              <span style={{ fontSize: '12.5px', fontWeight: 680, color: 'var(--txt)' }}>Research brief</span>
              <span style={{ marginLeft: 'auto', fontSize: '11px', fontWeight: 600, color: '#8b5cf6', background: 'rgba(139,92,246,0.14)', padding: '2px 8px', borderRadius: '10px' }}>
                {sources.length} source{sources.length !== 1 ? 's' : ''} · Google Search
              </span>
            </div>

            {/* TL;DR callout */}
            {tldr && (
              <div style={{ display: 'flex', gap: '8px', padding: '10px 13px', borderBottom: '1px solid var(--line)', background: 'var(--chip)' }}>
                <span style={{ fontSize: '10.5px', fontWeight: 750, letterSpacing: '.05em', color: '#8b5cf6', paddingTop: '1px' }}>TL;DR</span>
                <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--txt)', lineHeight: 1.4 }}>{tldr}</span>
              </div>
            )}

            {/* Findings (table + takeaways) */}
            {findings && (
              <div style={{ maxHeight: '300px', overflow: 'auto', padding: '11px 13px' }}>
                <MiniMarkdown text={findings} />
              </div>
            )}

            {/* Sources as compact domain chips */}
            {sources.length > 0 && (
              <div style={{ borderTop: '1px solid var(--line)', padding: '9px 13px', background: 'var(--chip)' }}>
                <div style={{ fontSize: '10.5px', fontWeight: 650, textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--faint)', marginBottom: '6px' }}>
                  Cited sources
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {sources.map((s, i) => (
                    <a key={i} href={s.url} target="_blank" rel="noreferrer" title={s.title}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '11.5px', color: 'var(--accent)', textDecoration: 'none', background: 'var(--panel, #fff)', border: '1px solid var(--line)', padding: '3px 9px', borderRadius: '20px', maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      🔗 {domain(s.url)}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {action.category === 'task' && (() => {
        const art = action.artifact || '';
        const url = art.match(/Plane:\s*(\S+)/);
        if (!url) return null;
        const ref = art.match(/Ref:\s*(\S+)/);
        const project = art.match(/Project:\s*(.+)/);
        const state = art.match(/State:\s*(.+)/);
        const priority = art.match(/Priority:\s*(.+)/);
        // Body = text after the metadata block (blank line following Labels:).
        const rest = art.match(/Labels:.*\n\s*\n([\s\S]*)$/);
        let title = '', body = '';
        if (rest) {
          const lines = rest[1].trim().split('\n');
          title = lines[0] || '';
          body = lines.slice(1).join('\n').trim();
        }
        const chip = {
          display: 'inline-flex', alignItems: 'center', gap: '5px', fontSize: '11.5px',
          padding: '3px 9px', borderRadius: '6px', background: 'var(--chip)',
          border: '1px solid var(--line)', color: 'var(--muted)', whiteSpace: 'nowrap',
        } as const;
        return (
          <div style={{ marginTop: '11px', border: '1px solid var(--line)', borderRadius: '10px', overflow: 'hidden', background: 'var(--panel, #fff)' }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '7px', padding: '10px 12px', borderBottom: '1px solid var(--line)' }}>
              <span style={chip}>📋 Plane · {project ? project[1].trim() : 'Understudy'}</span>
              {ref && <span style={chip}>{ref[1]}</span>}
              {state && <span style={{ ...chip, color: '#64748b', borderColor: '#64748b' }}>{state[1].trim()}</span>}
              {priority && <span style={chip}>⚑ {priority[1].trim()}</span>}
            </div>
            {(title || body) && (
              <div style={{ padding: '10px 12px' }}>
                {title && <div style={{ fontWeight: 650, fontSize: '13px', marginBottom: '4px' }}>{title}</div>}
                {body && <div style={{ fontSize: '12.5px', color: 'var(--muted)', lineHeight: 1.5 }}>{body}</div>}
              </div>
            )}
            <div style={{ borderTop: '1px solid var(--line)', padding: '9px 12px' }}>
              <a href={url[1]} target="_blank" rel="noreferrer" style={{ color: 'var(--accent)', textDecoration: 'none', fontWeight: 600, fontSize: '12.5px' }}>
                Open in Plane →
              </a>
            </div>
          </div>
        );
      })()}

      {isPending && (
        <div className="approve" style={{ display: 'flex', gap: '8px', marginTop: '11px' }}>
          <button
            className="btn primary"
            onClick={() => approveAction(action.id)}
            style={{
              fontSize: '12px',
              fontWeight: 650,
              padding: '7px 13px',
              borderRadius: '8px',
              border: '1px solid var(--accent)',
              background: 'var(--accent)',
              color: 'var(--on-accent)',
              cursor: 'pointer',
            }}
          >
            {action.category === 'code' ? 'Approve & open PR' : 'Approve & send'}
          </button>
          <button
            className="btn"
            onClick={() => editAction(action.id)}
            style={{
              fontSize: '12px',
              fontWeight: 650,
              padding: '7px 13px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
              background: 'var(--chip)',
              color: 'var(--txt)',
              cursor: 'pointer',
            }}
          >
            Edit
          </button>
          <button
            className="btn"
            onClick={() => skipAction(action.id)}
            style={{
              fontSize: '12px',
              fontWeight: 650,
              padding: '7px 13px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
              background: 'var(--chip)',
              color: 'var(--txt)',
              cursor: 'pointer',
            }}
          >
            Skip
          </button>
        </div>
      )}
    </div>
  );
};
