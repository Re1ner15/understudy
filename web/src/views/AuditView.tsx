import React, { useState, useEffect, useMemo } from 'react';
import { subscribeToAudit } from '../data';
import { AuditSpan, AuditCategory, AuditSpanStatus } from '../data/types';

const CategoryIcon: React.FC<{ category: AuditCategory; size?: number }> = ({ category, size = 15 }) => {
  const iconProps = {
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2,
    style: { width: `${size}px`, height: `${size}px` },
  };

  switch (category) {
    case 'orchestrator':
      return (
        <svg {...iconProps}>
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      );
    case 'llm':
      return (
        <svg {...iconProps}>
          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
        </svg>
      );
    case 'tool':
      return (
        <svg {...iconProps}>
          <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z" />
        </svg>
      );
    case 'screen':
      return (
        <svg {...iconProps}>
          <rect x="2" y="3" width="20" height="14" rx="2" />
          <line x1="8" y1="21" x2="16" y2="21" />
          <line x1="12" y1="17" x2="12" y2="21" />
        </svg>
      );
    case 'transcription':
      return (
        <svg {...iconProps}>
          <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="22" />
        </svg>
      );
    case 'scanner':
    default:
      return (
        <svg {...iconProps}>
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      );
  }
};

const getCategoryColor = (category: AuditCategory) => {
  switch (category) {
    case 'orchestrator':
      return { text: 'var(--accent)', bg: 'var(--accent-soft)', border: 'var(--accent-soft2)' };
    case 'llm':
      return { text: 'var(--purple)', bg: 'var(--purple-soft)', border: 'var(--purple-bd)' };
    case 'tool':
      return { text: 'var(--run)', bg: 'var(--run-soft)', border: 'rgba(59, 130, 246, 0.3)' };
    case 'screen':
      return { text: 'var(--amber)', bg: 'var(--amber-soft)', border: 'var(--amber-bd)' };
    case 'transcription':
      return { text: '#0891b2', bg: 'rgba(8, 145, 178, 0.1)', border: 'rgba(8, 145, 178, 0.25)' };
    case 'scanner':
    default:
      return { text: 'var(--muted)', bg: 'var(--chip)', border: 'var(--line)' };
  }
};

export const AuditView: React.FC = () => {
  const [spans, setSpans] = useState<AuditSpan[]>([]);
  const [selectedSpanId, setSelectedSpanId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'tree' | 'timeline'>('tree');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');

  useEffect(() => {
    const unsub = subscribeToAudit((items) => {
      setSpans(items);
      if (items.length > 0 && !selectedSpanId) {
        setSelectedSpanId(items[0].id);
      }
    });
    return unsub;
  }, [selectedSpanId]);

  // Derived metrics
  const totalLatencyMs = useMemo(() => {
    return spans.reduce((sum, s) => sum + (s.latencyMs || 0), 0);
  }, [spans]);

  const llmSpans = useMemo(() => spans.filter((s) => s.category === 'llm' || s.model), [spans]);
  const totalTokens = useMemo(() => {
    return spans.reduce((sum, s) => sum + (s.tokens?.total || 0), 0);
  }, [spans]);

  const filteredSpans = useMemo(() => {
    return spans.filter((s) => {
      if (categoryFilter !== 'all' && s.category !== categoryFilter) return false;
      if (statusFilter !== 'all' && s.status !== statusFilter) return false;
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesName = s.name.toLowerCase().includes(q);
        const matchesReason = s.reasoning?.toLowerCase().includes(q) || false;
        const matchesInput = s.inputSummary?.toLowerCase().includes(q) || false;
        const matchesOutput = s.outputSummary?.toLowerCase().includes(q) || false;
        if (!matchesName && !matchesReason && !matchesInput && !matchesOutput) return false;
      }
      return true;
    });
  }, [spans, categoryFilter, statusFilter, searchQuery]);

  const selectedSpan = useMemo(() => {
    return spans.find((s) => s.id === selectedSpanId) || filteredSpans[0] || null;
  }, [spans, selectedSpanId, filteredSpans]);

  // Build tree hierarchy for Tree view
  const rootSpans = useMemo(() => {
    const map = new Map<string, AuditSpan>();
    spans.forEach((s) => map.set(s.id, s));

    const roots: AuditSpan[] = [];
    filteredSpans.forEach((s) => {
      if (!s.parentId || !map.has(s.parentId)) {
        roots.push(s);
      }
    });
    return roots;
  }, [spans, filteredSpans]);

  const getChildSpans = (parentId: string): AuditSpan[] => {
    return filteredSpans.filter((s) => s.parentId === parentId);
  };

  const maxLatency = useMemo(() => {
    return Math.max(...spans.map((s) => s.latencyMs || 0), 100);
  }, [spans]);

  return (
    <div
      className="page"
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 54px)',
        overflow: 'hidden',
        background: 'var(--bg)',
      }}
    >
      {/* Top Header & Metrics Bar */}
      <div
        style={{
          background: 'var(--panel)',
          borderBottom: '1px solid var(--line)',
          padding: '16px 24px 14px',
          flexShrink: 0,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: '14px',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  letterSpacing: '.06em',
                  color: 'var(--purple)',
                  background: 'var(--purple-soft)',
                  padding: '2px 8px',
                  borderRadius: '6px',
                }}
              >
                Reasoning Trace
              </span>
              <span style={{ fontSize: '12px', color: 'var(--faint)' }}>·</span>
              <span style={{ fontSize: '12.5px', color: 'var(--muted)', fontWeight: 500 }}>
                Live Execution Graph &amp; Model Chain
              </span>
            </div>
            <h1
              style={{
                fontSize: '20px',
                fontWeight: 700,
                color: 'var(--txt)',
                letterSpacing: '-.02em',
              }}
            >
              Agent Reasoning &amp; Audit Trace
            </h1>
          </div>

          {/* View mode toggle */}
          <div
            style={{
              display: 'flex',
              background: 'var(--seg)',
              border: '1px solid var(--line)',
              borderRadius: '8px',
              padding: '2px',
            }}
          >
            <button
              onClick={() => setViewMode('tree')}
              style={{
                border: 0,
                background: viewMode === 'tree' ? 'var(--panel)' : 'none',
                color: viewMode === 'tree' ? 'var(--txt)' : 'var(--muted)',
                fontSize: '12.5px',
                fontWeight: 600,
                padding: '5px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                boxShadow: viewMode === 'tree' ? 'var(--seg-sh)' : 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 10h4M17 14h4M7 10h4M7 14h4M12 3v18" />
                <rect x="3" y="3" width="18" height="18" rx="2" />
              </svg>
              Reasoning Chain
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              style={{
                border: 0,
                background: viewMode === 'timeline' ? 'var(--panel)' : 'none',
                color: viewMode === 'timeline' ? 'var(--txt)' : 'var(--muted)',
                fontSize: '12.5px',
                fontWeight: 600,
                padding: '5px 12px',
                borderRadius: '6px',
                cursor: 'pointer',
                boxShadow: viewMode === 'timeline' ? 'var(--seg-sh)' : 'none',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="18" y1="20" x2="18" y2="10" />
                <line x1="12" y1="20" x2="12" y2="4" />
                <line x1="6" y1="20" x2="6" y2="14" />
              </svg>
              Timeline Waterfall
            </button>
          </div>
        </div>

        {/* Metric tiles */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
            gap: '12px',
          }}
        >
          <div
            style={{
              background: 'var(--chip)',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              Total Spans
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--txt)', marginTop: '2px' }}>
              {spans.length}
            </div>
          </div>

          <div
            style={{
              background: 'var(--chip)',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              Cumulative Latency
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--txt)', marginTop: '2px' }}>
              {(totalLatencyMs / 1000).toFixed(2)}s
            </div>
          </div>

          <div
            style={{
              background: 'var(--chip)',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              Gemini 3.5 Flash Calls
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--purple)', marginTop: '2px' }}>
              {llmSpans.length}
            </div>
          </div>

          <div
            style={{
              background: 'var(--chip)',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              Model Tokens (In/Out)
            </div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--txt)', marginTop: '2px' }}>
              {totalTokens.toLocaleString()}
            </div>
          </div>

          <div
            style={{
              background: 'var(--chip)',
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid var(--line)',
            }}
          >
            <div style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '.04em' }}>
              Status
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px', fontSize: '12px' }}>
              <span style={{ color: 'var(--done)', fontWeight: 650 }}>
                {spans.filter((s) => s.status === 'done').length} done
              </span>
              {spans.filter((s) => s.status === 'running').length > 0 && (
                <span style={{ color: 'var(--run)', fontWeight: 650 }}>
                  {spans.filter((s) => s.status === 'running').length} live
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        style={{
          padding: '10px 24px',
          background: 'var(--panel)',
          borderBottom: '1px solid var(--line)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
          flexShrink: 0,
        }}
      >
        {/* Category filters */}
        <div style={{ display: 'flex', gap: '5px', alignItems: 'center', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '11.5px', color: 'var(--faint)', fontWeight: 600, marginRight: '4px' }}>
            Category:
          </span>
          {['all', 'orchestrator', 'llm', 'tool', 'screen', 'transcription'].map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              style={{
                background: categoryFilter === cat ? 'var(--chip)' : 'transparent',
                border: `1px solid ${categoryFilter === cat ? 'var(--line)' : 'transparent'}`,
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '11.5px',
                fontWeight: categoryFilter === cat ? 650 : 500,
                color: categoryFilter === cat ? 'var(--txt)' : 'var(--muted)',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {cat === 'all' ? 'All' : cat === 'llm' ? 'LLM Models' : cat}
            </button>
          ))}
        </div>

        {/* Status filters */}
        <div style={{ display: 'flex', gap: '5px', alignItems: 'center', marginLeft: 'auto' }}>
          <span style={{ fontSize: '11.5px', color: 'var(--faint)', fontWeight: 600, marginRight: '4px' }}>
            Status:
          </span>
          {['all', 'done', 'running', 'queued', 'error'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              style={{
                background: statusFilter === st ? 'var(--chip)' : 'transparent',
                border: `1px solid ${statusFilter === st ? 'var(--line)' : 'transparent'}`,
                borderRadius: '6px',
                padding: '3px 8px',
                fontSize: '11.5px',
                fontWeight: statusFilter === st ? 650 : 500,
                color: statusFilter === st ? 'var(--txt)' : 'var(--muted)',
                cursor: 'pointer',
                textTransform: 'capitalize',
              }}
            >
              {st}
            </button>
          ))}
        </div>

        {/* Search */}
        <div style={{ width: '180px' }}>
          <input
            type="text"
            placeholder="Search spans..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              padding: '4px 8px',
              fontSize: '12px',
              borderRadius: '6px',
              border: '1px solid var(--line)',
              background: 'var(--bg)',
              color: 'var(--txt)',
              outline: 'none',
            }}
          />
        </div>
      </div>

      {/* Main Content Area: Left list (Tree/Timeline) + Right Inspector */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '55% 45%',
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {/* Left column: Tree or Timeline Waterfall */}
        <div
          style={{
            overflowY: 'auto',
            padding: '16px 20px',
            borderRight: '1px solid var(--line)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            background: 'var(--bg)',
          }}
        >
          {filteredSpans.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px 16px', color: 'var(--muted)', fontSize: '13px' }}>
              No audit spans match the current filters.
            </div>
          ) : viewMode === 'tree' ? (
            // TREE VIEW
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {rootSpans.map((root) => (
                <TreeNode
                  key={root.id}
                  span={root}
                  depth={0}
                  selectedId={selectedSpan?.id || null}
                  onSelect={setSelectedSpanId}
                  getChildSpans={getChildSpans}
                />
              ))}
            </div>
          ) : (
            // TIMELINE WATERFALL VIEW
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {filteredSpans.map((span) => {
                const isSelected = selectedSpan?.id === span.id;
                const catStyle = getCategoryColor(span.category);
                const widthPercent = Math.max(8, Math.min(100, (span.latencyMs / maxLatency) * 100));

                return (
                  <div
                    key={span.id}
                    onClick={() => setSelectedSpanId(span.id)}
                    style={{
                      background: isSelected ? 'var(--panel)' : 'var(--panel)',
                      border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--line)'}`,
                      borderRadius: '10px',
                      padding: '10px 14px',
                      cursor: 'pointer',
                      boxShadow: isSelected ? '0 0 0 1.5px var(--accent), var(--card-sh)' : 'var(--card-sh)',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div
                          style={{
                            width: '24px',
                            height: '24px',
                            borderRadius: '6px',
                            background: catStyle.bg,
                            border: `1px solid ${catStyle.border}`,
                            color: catStyle.text,
                            display: 'grid',
                            placeItems: 'center',
                            flexShrink: 0,
                          }}
                        >
                          <CategoryIcon category={span.category} size={13} />
                        </div>
                        <span style={{ fontSize: '13px', fontWeight: 650, color: 'var(--txt)' }}>
                          {span.name}
                        </span>
                        {span.model && (
                          <span
                            style={{
                              fontSize: '10.5px',
                              fontWeight: 650,
                              color: 'var(--purple)',
                              background: 'var(--purple-soft)',
                              padding: '1px 6px',
                              borderRadius: '4px',
                            }}
                          >
                            {span.model}
                          </span>
                        )}
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '11px', color: 'var(--faint)', fontVariantNumeric: 'tabular-nums' }}>
                          {span.startTime}
                        </span>
                        <StatusBadge status={span.status} />
                      </div>
                    </div>

                    {/* Latency Waterfall Bar */}
                    <div style={{ marginTop: '6px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: 'var(--muted)', marginBottom: '3px' }}>
                        <span>Duration</span>
                        <span style={{ fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>{span.latencyMs}ms</span>
                      </div>
                      <div
                        style={{
                          height: '6px',
                          width: '100%',
                          background: 'var(--chip)',
                          borderRadius: '3px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            height: '100%',
                            width: `${widthPercent}%`,
                            background: catStyle.text,
                            borderRadius: '3px',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right column: Span Inspector */}
        <div
          style={{
            overflowY: 'auto',
            padding: '20px 24px',
            background: 'var(--panel)',
            display: 'flex',
            flexDirection: 'column',
            gap: '16px',
          }}
        >
          {selectedSpan ? (
            <div>
              {/* Top Details */}
              <div style={{ borderBottom: '1px solid var(--line)', paddingBottom: '16px', marginBottom: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '.05em',
                      color: getCategoryColor(selectedSpan.category).text,
                      background: getCategoryColor(selectedSpan.category).bg,
                      border: `1px solid ${getCategoryColor(selectedSpan.category).border}`,
                      padding: '2px 8px',
                      borderRadius: '6px',
                    }}
                  >
                    {selectedSpan.category}
                  </span>
                  <StatusBadge status={selectedSpan.status} />
                  {selectedSpan.model && (
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 650,
                        color: 'var(--purple)',
                        background: 'var(--purple-soft)',
                        padding: '2px 8px',
                        borderRadius: '6px',
                      }}
                    >
                      {selectedSpan.model}
                    </span>
                  )}
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: '12px',
                      color: 'var(--muted)',
                      fontWeight: 600,
                      fontVariantNumeric: 'tabular-nums',
                    }}
                  >
                    {selectedSpan.latencyMs}ms
                  </span>
                </div>

                <h2 style={{ fontSize: '17px', fontWeight: 700, color: 'var(--txt)', lineHeight: 1.3 }}>
                  {selectedSpan.name}
                </h2>
                <div style={{ fontSize: '11.5px', color: 'var(--faint)', marginTop: '4px', fontVariantNumeric: 'tabular-nums' }}>
                  Span ID: <code style={{ color: 'var(--txt)', background: 'var(--chip)', padding: '1px 5px', borderRadius: '4px' }}>{selectedSpan.id}</code>
                  {selectedSpan.parentId && (
                    <> · Parent: <code style={{ color: 'var(--txt)', background: 'var(--chip)', padding: '1px 5px', borderRadius: '4px' }}>{selectedSpan.parentId}</code></>
                  )}
                  {selectedSpan.startTime && (
                    <> · Executed: {selectedSpan.startTime} {selectedSpan.endTime ? `→ ${selectedSpan.endTime}` : ''}</>
                  )}
                </div>
              </div>

              {/* Token breakdown if present */}
              {selectedSpan.tokens && (
                <div
                  style={{
                    background: 'var(--chip)',
                    border: '1px solid var(--line)',
                    borderRadius: '10px',
                    padding: '12px 14px',
                    marginBottom: '16px',
                  }}
                >
                  <div style={{ fontSize: '11.5px', fontWeight: 700, color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '.04em', marginBottom: '8px' }}>
                    Token Consumption (Gemini API)
                  </div>
                  <div style={{ display: 'flex', gap: '20px', fontSize: '12.5px' }}>
                    <div>
                      <span style={{ color: 'var(--faint)' }}>Prompt: </span>
                      <strong style={{ color: 'var(--txt)' }}>{selectedSpan.tokens.prompt || 0}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--faint)' }}>Completion: </span>
                      <strong style={{ color: 'var(--txt)' }}>{selectedSpan.tokens.completion || 0}</strong>
                    </div>
                    <div>
                      <span style={{ color: 'var(--faint)' }}>Total: </span>
                      <strong style={{ color: 'var(--purple)' }}>{selectedSpan.tokens.total || 0}</strong>
                    </div>
                  </div>
                </div>
              )}

              {/* Agent Reasoning Trace */}
              {selectedSpan.reasoning && (
                <div style={{ marginBottom: '16px' }}>
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '12px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '.05em',
                      color: 'var(--faint)',
                      marginBottom: '8px',
                    }}
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                    Reasoning &amp; Chain-of-Thought
                  </div>
                  <div
                    style={{
                      background: 'var(--chip)',
                      border: '1px solid var(--line)',
                      borderLeft: '3px solid var(--accent)',
                      borderRadius: '8px',
                      padding: '12px 14px',
                      fontSize: '13px',
                      color: 'var(--txt)',
                      lineHeight: 1.55,
                      whiteSpace: 'pre-wrap',
                      fontFamily: 'inherit',
                    }}
                  >
                    {selectedSpan.reasoning}
                  </div>
                </div>
              )}

              {/* Input Summary */}
              {selectedSpan.inputSummary && (
                <div style={{ marginBottom: '16px' }}>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '.05em',
                      color: 'var(--faint)',
                      marginBottom: '8px',
                    }}
                  >
                    Input Payload / Context
                  </div>
                  <div
                    style={{
                      background: 'var(--chip)',
                      border: '1px solid var(--line)',
                      borderRadius: '8px',
                      padding: '10px 14px',
                      fontSize: '12.5px',
                      color: 'var(--muted)',
                      lineHeight: 1.45,
                    }}
                  >
                    {selectedSpan.inputSummary}
                  </div>
                </div>
              )}

              {/* Output Summary */}
              {selectedSpan.outputSummary && (
                <div style={{ marginBottom: '16px' }}>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '.05em',
                      color: 'var(--faint)',
                      marginBottom: '8px',
                    }}
                  >
                    Output / Extracted Artifact
                  </div>
                  <div
                    style={{
                      background: 'var(--chip)',
                      border: '1px solid var(--line)',
                      borderRadius: '8px',
                      padding: '10px 14px',
                      fontSize: '12.5px',
                      color: 'var(--txt)',
                      lineHeight: 1.45,
                    }}
                  >
                    {selectedSpan.outputSummary}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--muted)' }}>
              Select a span from the left to inspect its reasoning trace and metadata.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Tree Node recursive component
interface TreeNodeProps {
  span: AuditSpan;
  depth: number;
  selectedId: string | null;
  onSelect: (id: string) => void;
  getChildSpans: (id: string) => AuditSpan[];
}

const TreeNode: React.FC<TreeNodeProps> = ({
  span,
  depth,
  selectedId,
  onSelect,
  getChildSpans,
}) => {
  const isSelected = selectedId === span.id;
  const children = getChildSpans(span.id);
  const catStyle = getCategoryColor(span.category);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <div
        onClick={() => onSelect(span.id)}
        style={{
          marginLeft: `${depth * 22}px`,
          position: 'relative',
          background: isSelected ? 'var(--panel)' : 'var(--panel)',
          border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--line)'}`,
          borderRadius: '10px',
          padding: '10px 14px',
          cursor: 'pointer',
          boxShadow: isSelected ? '0 0 0 1.5px var(--accent), var(--card-sh)' : 'var(--card-sh)',
          transition: 'all 0.15s ease',
        }}
      >
        {/* Tree branch connector line */}
        {depth > 0 && (
          <div
            style={{
              position: 'absolute',
              left: '-14px',
              top: '18px',
              width: '12px',
              height: '1px',
              background: 'var(--line)',
            }}
          />
        )}

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
            <div
              style={{
                width: '24px',
                height: '24px',
                borderRadius: '6px',
                background: catStyle.bg,
                border: `1px solid ${catStyle.border}`,
                color: catStyle.text,
                display: 'grid',
                placeItems: 'center',
                flexShrink: 0,
              }}
            >
              <CategoryIcon category={span.category} size={13} />
            </div>

            <span
              style={{
                fontSize: '13px',
                fontWeight: 650,
                color: 'var(--txt)',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
              }}
            >
              {span.name}
            </span>

            {span.model && (
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 650,
                  color: 'var(--purple)',
                  background: 'var(--purple-soft)',
                  padding: '1px 5px',
                  borderRadius: '4px',
                  flexShrink: 0,
                }}
              >
                {span.model}
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <span style={{ fontSize: '11px', color: 'var(--muted)', fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
              {span.latencyMs}ms
            </span>
            <StatusBadge status={span.status} />
          </div>
        </div>

        {span.reasoning && (
          <div
            style={{
              fontSize: '12px',
              color: 'var(--muted)',
              marginTop: '6px',
              lineHeight: 1.35,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            ↳ {span.reasoning}
          </div>
        )}
      </div>

      {/* Render children recursively */}
      {children.length > 0 && (
        <div
          style={{
            position: 'relative',
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
            marginLeft: depth > 0 ? `${depth * 22}px` : '0px',
            borderLeft: depth === 0 ? '1.5px solid var(--line)' : 'none',
            paddingLeft: depth === 0 ? '8px' : '0px',
          }}
        >
          {children.map((child) => (
            <TreeNode
              key={child.id}
              span={child}
              depth={depth === 0 ? 1 : depth + 1}
              selectedId={selectedId}
              onSelect={onSelect}
              getChildSpans={getChildSpans}
            />
          ))}
        </div>
      )}
    </div>
  );
};

const StatusBadge: React.FC<{ status: AuditSpanStatus }> = ({ status }) => {
  switch (status) {
    case 'done':
      return (
        <span
          style={{
            fontSize: '10.5px',
            fontWeight: 650,
            color: 'var(--done)',
            background: 'var(--done-soft)',
            padding: '2px 6px',
            borderRadius: '6px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '3px',
          }}
        >
          ✓ done
        </span>
      );
    case 'running':
      return (
        <span
          style={{
            fontSize: '10.5px',
            fontWeight: 650,
            color: 'var(--run)',
            background: 'var(--run-soft)',
            padding: '2px 6px',
            borderRadius: '6px',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
          }}
        >
          <span
            style={{
              width: '8px',
              height: '8px',
              borderRadius: '50%',
              border: '1.5px solid var(--run)',
              borderRightColor: 'transparent',
              animation: 'spin .8s linear infinite',
            }}
          />
          running
        </span>
      );
    case 'error':
      return (
        <span
          style={{
            fontSize: '10.5px',
            fontWeight: 650,
            color: 'var(--red)',
            background: 'var(--red-soft)',
            padding: '2px 6px',
            borderRadius: '6px',
          }}
        >
          error
        </span>
      );
    case 'queued':
    default:
      return (
        <span
          style={{
            fontSize: '10.5px',
            fontWeight: 600,
            color: 'var(--faint)',
            background: 'var(--chip)',
            padding: '2px 6px',
            borderRadius: '6px',
          }}
        >
          queued
        </span>
      );
  }
};
