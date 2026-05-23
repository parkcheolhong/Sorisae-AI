'use client';

import { useEffect, useState } from 'react';
import { ExecutionBoard } from './executionboard';
import { FocusRail } from './focusrail';
import { HeroPanel } from './heropanel';
import { InsightTimeline } from './insighttimeline';
import { MetricCluster } from './metriccluster';
import { SignalMatrix } from './signalmatrix';
import { ThemeToggle } from './themetoggle';
import type { BriefPayload } from '../lib/types';

type DashboardVariant = 'overview' | 'detail';

async function readBrief(): Promise<BriefPayload> {
  const response = await fetch('/api/brief', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`brief fetch failed: ${response.status}`);
  }
  return response.json() as Promise<BriefPayload>;
}

export function DashboardClient({ initialPayload, variant }: { initialPayload: BriefPayload; variant: DashboardVariant }) {
  const [payload, setPayload] = useState(initialPayload);
  const [phase, setPhase] = useState<'idle' | 'loading' | 'live' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState('');

  const refresh = async () => {
    setPhase('loading');
    setErrorMessage('');
    try {
      const nextPayload = await readBrief();
      setPayload(nextPayload);
      setPhase('live');
    } catch (error) {
      setPhase('error');
      setErrorMessage(error instanceof Error ? error.message : 'brief fetch failed');
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const runtimeItems = payload.runtimeSignals.map((signal) => `${signal.label}: ${signal.status} · ${signal.owner}`);
  const pillClassName = phase === 'error' ? 'statusPill is-error' : phase === 'live' ? 'statusPill is-live' : 'statusPill';

  return (
    <main className="page dashboardStack">
      <section className="sectionCard utilityBar">
        <div className="utilityGroup">
          <div className="statusPill">Variant · {variant}</div>
          <div className={pillClassName}>Fetch · {phase}</div>
          <div className="statusPill">Refreshed · {payload.refreshedAt}</div>
        </div>
        <div className="utilityGroup">
          <ThemeToggle />
          <button type="button" className="refreshButton" onClick={() => void refresh()}>Refresh live brief</button>
        </div>
      </section>
      {phase === 'error' ? <section className="sectionCard"><p className="eyebrow">Fetch warning</p><p>{errorMessage}</p></section> : null}
      {variant === 'overview' ? (
        <>
          <HeroPanel summary={payload.summary} />
          <MetricCluster metrics={payload.metrics} />
          <SignalMatrix signals={payload.runtimeSignals} />
          <section className="featureGrid">
            <FocusRail title="Focus rail" items={payload.focusRail} />
            <InsightTimeline title="Release timeline" items={payload.releaseTimeline} />
          </section>
        </>
      ) : (
        <>
          <header className="sectionCard sectionHeader">
            <div>
              <p className="eyebrow">Dashboard</p>
              <h1>Operational release cockpit</h1>
              <p className="muted sectionCopy">This view compresses the same live brief into a denser board for owners and release reviewers.</p>
            </div>
            <a href="/api/brief" className="textLink">Open raw brief JSON</a>
          </header>
          <MetricCluster metrics={payload.metrics} compact />
          <section className="featureGrid">
            <ExecutionBoard title="Runtime signals" items={runtimeItems} />
            <InsightTimeline title="Release timeline" items={payload.releaseTimeline} />
          </section>
        </>
      )}
    </main>
  );
}
