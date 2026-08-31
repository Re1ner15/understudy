import React, { useEffect, useState } from 'react';
import { listPastMeetings, getMeetingDetail } from '../data';
import { PastMeetingSummary, TranscriptLine, Minutes } from '../data/types';

type Detail = { id: string; title: string; date: string; transcript: TranscriptLine[]; minutes: Minutes | null };

export const HistoryView: React.FC = () => {
  const [meetings, setMeetings] = useState<PastMeetingSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [tab, setTab] = useState<'minutes' | 'transcript'>('minutes');

  useEffect(() => {
    listPastMeetings().then((m) => {
      setMeetings(m);
      if (m.length && !selected) setSelected(m[0].id);
    });
  }, []);

  useEffect(() => {
    if (selected) getMeetingDetail(selected).then(setDetail);
  }, [selected]);

  return (
    <div className="body" style={{ flex: 1, display: 'flex', minHeight: 0 }}>
      {/* Left: meeting list */}
      <div style={{ width: '280px', borderRight: '1px solid var(--line)', overflowY: 'auto', flex: 'none' }}>
        <div style={{ padding: '17px 20px 10px', fontSize: '12px', textTransform: 'uppercase', letterSpacing: '.08em', color: 'var(--faint)', fontWeight: 650 }}>
          Past meetings
        </div>
        {meetings.map((m) => (
          <button
            key={m.id}
            onClick={() => setSelected(m.id)}
            style={{
              display: 'block', width: '100%', textAlign: 'left', border: 0, cursor: 'pointer',
              padding: '12px 20px',
              background: selected === m.id ? 'var(--chip)' : 'none',
              borderLeft: `3px solid ${selected === m.id ? 'var(--accent)' : 'transparent'}`,
            }}
          >
            <div style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--txt)' }}>{m.title}</div>
            <div style={{ fontSize: '12px', color: 'var(--faint)', marginTop: '2px' }}>{m.date}</div>
          </button>
        ))}
        {meetings.length === 0 && (
          <div style={{ padding: '20px', fontSize: '12.5px', color: 'var(--faint)' }}>No past meetings yet.</div>
        )}
      </div>

      {/* Right: detail */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '22px 26px' }}>
        {!detail ? (
          <div style={{ color: 'var(--faint)', fontSize: '13px' }}>Select a meeting…</div>
        ) : (
          <>
            <h1 style={{ fontSize: '22px', fontWeight: 700 }}>{detail.title}</h1>
            <div style={{ color: 'var(--faint)', fontSize: '13px', marginTop: '2px' }}>{detail.date}</div>

            <div style={{ display: 'flex', gap: '6px', margin: '16px 0' }}>
              {(['minutes', 'transcript'] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    border: `1px solid ${tab === t ? 'var(--accent)' : 'var(--line)'}`,
                    background: tab === t ? 'var(--accent)' : 'var(--chip)',
                    color: tab === t ? 'var(--on-accent)' : 'var(--muted)',
                    fontSize: '12.5px', fontWeight: 600, padding: '6px 14px', borderRadius: '8px', cursor: 'pointer',
                    textTransform: 'capitalize',
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            {tab === 'minutes' ? (
              detail.minutes ? (
                <div style={{ maxWidth: '720px' }}>
                  {detail.minutes.attendees?.length > 0 && (
                    <section style={{ marginBottom: '20px' }}>
                      <h3 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--faint)', marginBottom: '8px' }}>Attendees</h3>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                        {detail.minutes.attendees.map((a, i) => (
                          <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12.5px', fontWeight: 600, color: 'var(--txt)', background: 'var(--chip)', border: '1px solid var(--line)', padding: '4px 10px 4px 6px', borderRadius: '20px' }}>
                            <span style={{ width: '18px', height: '18px', borderRadius: '50%', background: 'var(--accent)', color: 'var(--on-accent)', fontSize: '10px', fontWeight: 700, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>{a[0]}</span>
                            {a}
                          </span>
                        ))}
                      </div>
                    </section>
                  )}
                  {detail.minutes.decisions?.length > 0 && (
                    <section style={{ marginBottom: '20px' }}>
                      <h3 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--faint)', marginBottom: '8px' }}>Decisions</h3>
                      {detail.minutes.decisions.map((d, i) => (
                        <div key={i} style={{ fontSize: '13.5px', color: 'var(--txt)', padding: '3px 0', display: 'flex', gap: '8px' }}>
                          <span style={{ color: 'var(--accent)' }}>✓</span> {d}
                        </div>
                      ))}
                    </section>
                  )}
                  {detail.minutes.topics?.length > 0 && (
                    <section style={{ marginBottom: '20px' }}>
                      <h3 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--faint)', marginBottom: '8px' }}>Topics</h3>
                      {detail.minutes.topics.map((t, i) => (
                        <div key={i} style={{ marginBottom: '12px' }}>
                          <div style={{ fontWeight: 650, fontSize: '14px' }}>{t.heading}</div>
                          <div style={{ fontSize: '13px', color: 'var(--muted)', lineHeight: 1.5, marginTop: '3px' }}>{t.notes}</div>
                        </div>
                      ))}
                    </section>
                  )}
                  {detail.minutes.actionItems?.length > 0 && (
                    <section style={{ marginBottom: '20px' }}>
                      <h3 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--faint)', marginBottom: '8px' }}>Action items</h3>
                      {detail.minutes.actionItems.map((a, i) => (
                        <div key={a.id || i} style={{ display: 'flex', alignItems: 'baseline', gap: '10px', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
                          <span style={{ fontSize: '13.5px', color: 'var(--txt)', flex: 1 }}>{a.text}</span>
                          {a.assignee && (
                            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--muted)', whiteSpace: 'nowrap' }}>{a.assignee}</span>
                          )}
                          {a.due && (
                            <span style={{ fontSize: '11.5px', color: 'var(--faint)', whiteSpace: 'nowrap' }}>{a.due}</span>
                          )}
                        </div>
                      ))}
                    </section>
                  )}
                  {detail.minutes.materialsShown?.length > 0 && (
                    <section style={{ marginBottom: '20px' }}>
                      <h3 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '.06em', color: 'var(--faint)', marginBottom: '8px' }}>Materials shown</h3>
                      {detail.minutes.materialsShown.map((m, i) => (
                        <div key={i} style={{ fontSize: '13px', color: 'var(--muted)', padding: '3px 0', display: 'flex', gap: '8px' }}>
                          <span style={{ color: 'var(--faint)' }}>📎</span> {m}
                        </div>
                      ))}
                    </section>
                  )}
                </div>
              ) : (
                <div style={{ color: 'var(--faint)', fontSize: '13px' }}>No minutes for this meeting.</div>
              )
            ) : (
              <div style={{ maxWidth: '720px' }}>
                {detail.transcript.length === 0 && (
                  <div style={{ color: 'var(--faint)', fontSize: '13px' }}>No transcript for this meeting.</div>
                )}
                {detail.transcript.map((line) => (
                  <div key={line.id} style={{ display: 'flex', gap: '12px', padding: '6px 0' }}>
                    <span style={{ fontSize: '12px', color: 'var(--faint)', fontVariantNumeric: 'tabular-nums', flex: 'none', width: '58px' }}>{line.ts}</span>
                    <div>
                      <span style={{ fontWeight: 600, fontSize: '13px', marginRight: '6px' }}>{line.speaker}</span>
                      <span style={{ fontSize: '13.5px', color: 'var(--txt)', lineHeight: 1.5 }}>{line.text}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
