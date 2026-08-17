import {
    execSync
} from 'node:child_process';
import {
    existsSync,
    readFileSync
} from 'node:fs';
import {
    join
} from 'node:path';

const appRoot = process.cwd();
const easJsonPath = join(appRoot, 'eas.json');

function run(command) {
    return execSync(command, {
        cwd: appRoot,
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
    });
}

function fail(message) {
    process.stderr.write(`DRY_RUN_FAIL: ${message}\n`);
    process.exit(1);
}

function pass(message) {
    process.stdout.write(`DRY_RUN_PASS: ${message}\n`);
}

if (!existsSync(easJsonPath)) {
    fail(`eas.json not found: ${easJsonPath}`);
}

let eas;
try {
    eas = JSON.parse(readFileSync(easJsonPath, 'utf-8'));
} catch (error) {
    fail(`invalid eas.json: ${error instanceof Error ? error.message : String(error)}`);
}

if (!eas?.submit?.production) {
    fail('submit.production profile missing in eas.json');
}
pass('submit.production profile exists');

try {
    const gateOutput = run('node scripts/validate-production-submit-gate.mjs');
    if (!gateOutput.includes('GATE_PASS: production submit pre-check completed')) {
        fail('production gate did not report completion');
    }
    pass('production submit gate passed');
} catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    fail(`production gate command failed: ${message}`);
}

let submitHelp = '';
try {
    submitHelp = run('npx eas-cli submit --help');
} catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    fail(`failed to read eas submit help: ${message}`);
}

const requiredFlags = ['--platform', '--profile', '--latest', '--non-interactive'];
for (const flag of requiredFlags) {
    if (!submitHelp.includes(flag)) {
        fail(`required submit flag not found in help output: ${flag}`);
    }
}
pass(`submit help contains required flags: ${requiredFlags.join(', ')}`);

const dryRunCommand = 'npx eas-cli submit --platform android --profile production --latest --non-interactive';
pass(`validated command shape: ${dryRunCommand}`);
process.stdout.write('DRY_RUN_PASS: production submit dry-run checks completed\n');