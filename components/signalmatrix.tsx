import type { RuntimeSignal } from '../lib/types';

export function SignalMatrix({ signals }: { signals: RuntimeSignal[] }) {
  return (
    <section className="signalGrid">
      {signals.map((signal) => (
        <article key={signal.label} className="signalCard">
          <div className={`signalTone is-${signal.tone}`} />
          <div className="signalLabel">{signal.label}</div>
          <div className="signalStatus">{signal.status}</div>
          <p className="muted">{signal.detail}</p>
          <div className="microLabel">Owner · {signal.owner}</div>
        </article>
        ))}
    </section>
  );
}
