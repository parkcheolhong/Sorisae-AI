import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const appRoot = process.cwd();
const repoRoot = join(appRoot, '..', '..');
const packageJsonPath = join(appRoot, 'package.json');
const changelogPath = join(repoRoot, 'docs', 'mobile-stock-ai-changelog.md');
const approvalPath = join(repoRoot, 'docs', 'mobile-stock-ai-production-approval.md');

function fail(message) {
  process.stderr.write(`GATE_FAIL: ${message}\n`);
  process.exit(1);
}

function pass(message) {
  process.stdout.write(`GATE_PASS: ${message}\n`);
}

if (!existsSync(packageJsonPath)) {
  fail('package.json not found');
}

const pkg = JSON.parse(readFileSync(packageJsonPath, 'utf-8'));
const version = String(pkg?.version || '').trim();

if (!version || !/^\d+\.\d+\.\d+(-[\w.-]+)?$/.test(version)) {
  fail(`invalid version '${version}' in package.json`);
}
pass(`version format ok (${version})`);

if (!existsSync(changelogPath)) {
  fail(`changelog file not found: ${changelogPath}`);
}

const changelog = readFileSync(changelogPath, 'utf-8');
if (!changelog.includes(version)) {
  fail(`changelog does not include current version ${version}`);
}
pass(`changelog contains current version (${version})`);

if (!existsSync(approvalPath)) {
  fail(`approval file not found: ${approvalPath}`);
}

const approvalText = readFileSync(approvalPath, 'utf-8');
if (!/APPROVED\s*:\s*YES/i.test(approvalText)) {
  fail('approval gate requires line: APPROVED: YES');
}
pass('approval marker found');

process.stdout.write('GATE_PASS: production submit pre-check completed\n');
