import {
    execSync
} from 'node:child_process';
import {
    existsSync,
    readFileSync,
    writeFileSync
} from 'node:fs';
import {
    join
} from 'node:path';

const projectRoot = process.cwd();
const idStorePath = join(projectRoot, 'eas-project-id.json');
const envLocalPath = join(projectRoot, '.env.local');
const isDryRun = process.argv.includes('--dry-run');
const PLACEHOLDER_PROJECT_ID = '00000000-0000-0000-0000-000000000000';

function isPlaceholderProjectId(value) {
    return /^0{8}-0{4}-0{4}-0{4}-0{12}$/.test(String(value || '').trim());
}

function run(command) {
    return execSync(command, {
        cwd: projectRoot,
        encoding: 'utf-8',
        stdio: ['pipe', 'pipe', 'pipe'],
    });
}

function extractUuid(value) {
    const match = value.match(/[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i);
    return match ? match[0] : null;
}

function loadStoredProjectId() {
    if (!existsSync(idStorePath)) {
        return null;
    }

    try {
        const parsed = JSON.parse(readFileSync(idStorePath, 'utf-8'));
        const value = typeof parsed?.projectId === 'string' && parsed.projectId.trim() ? parsed.projectId.trim() : null;
        if (value && isPlaceholderProjectId(value)) {
            return null;
        }
        return value;
    } catch {
        return null;
    }
}

function writeProjectId(projectId) {
    writeFileSync(
        idStorePath,
        `${JSON.stringify({ projectId, updatedAt: new Date().toISOString() }, null, 2)}\n`,
        'utf-8',
    );
}

function upsertEnvLocal(projectId) {
    const line = `EXPO_PROJECT_ID=${projectId}`;
    if (!existsSync(envLocalPath)) {
        writeFileSync(envLocalPath, `${line}\n`, 'utf-8');
        return;
    }

    const content = readFileSync(envLocalPath, 'utf-8');
    const lines = content.split(/\r?\n/);
    const targetIndex = lines.findIndex((entry) => entry.startsWith('EXPO_PROJECT_ID='));

    if (targetIndex >= 0) {
        lines[targetIndex] = line;
    } else {
        lines.push(line);
    }

    writeFileSync(envLocalPath, `${lines.filter(Boolean).join('\n')}\n`, 'utf-8');
}

function ensureProjectLinked() {
    if (isDryRun) {
        const envId = String(process.env.EXPO_PROJECT_ID || '').trim();
        const dryId = (envId && !isPlaceholderProjectId(envId) ? envId : '') || loadStoredProjectId() || PLACEHOLDER_PROJECT_ID;
        return dryId;
    }

    try {
        const output = run('npx eas-cli project:info');
        const id = extractUuid(output);
        if (id) {
            return id;
        }
    } catch {
        // Continue to init flow
    }

    const envId = process.env.EXPO_PROJECT_ID && !isPlaceholderProjectId(process.env.EXPO_PROJECT_ID) ?
        process.env.EXPO_PROJECT_ID :
        null;
    const explicitId = envId || loadStoredProjectId();
    const initCommand = explicitId ?
        `npx eas-cli project:init --non-interactive --force --id ${explicitId}` :
        'npx eas-cli project:init --non-interactive --force';

    run(initCommand);

    const infoOutput = run('npx eas-cli project:info');
    const ensuredId = extractUuid(infoOutput);
    if (!ensuredId) {
        throw new Error('Unable to resolve EXPO_PROJECT_ID from eas project:info output.');
    }

    return ensuredId;
}

try {
    const projectId = ensureProjectLinked();
    if (isDryRun) {
        process.stdout.write(`EAS project dry-run: ${projectId}\n`);
        process.stdout.write(`Would store in: ${idStorePath}\n`);
        process.stdout.write(`Would update: ${envLocalPath}\n`);
    } else {
        writeProjectId(projectId);
        upsertEnvLocal(projectId);
        process.stdout.write(`EAS project linked: ${projectId}\n`);
        process.stdout.write(`Stored in: ${idStorePath}\n`);
        process.stdout.write(`Updated: ${envLocalPath}\n`);
    }
} catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    process.stderr.write(`Failed to ensure EXPO_PROJECT_ID: ${message}\n`);
    process.stderr.write('Run `npx eas-cli login` and retry if not authenticated.\n');
    process.exit(1);
}