import { config } from '../config';

export function readRuntimeSummary() {
  return {
    profile: config.runtimeProfile,
    readiness: 'ready',
  };
}
