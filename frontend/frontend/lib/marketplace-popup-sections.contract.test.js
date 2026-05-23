const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

function read(relativePath) {
    return fs.readFileSync(path.join(__dirname, '..', relativePath), 'utf8');
}

function includesAll(source, snippets, label) {
    for (const snippet of snippets) {
        assert.ok(source.includes(snippet), `${label} is missing snippet: ${snippet}`);
    }
}

const liveViewSection = read('components/marketplace/popup-sections/feature-popup-live-view-section.tsx');
includesAll(liveViewSection, [
    'data-testid="marketplace-live-view-panel"',
    'data-testid="marketplace-live-view-connection"',
    'data-testid="marketplace-live-view-spotlight"',
    'data-testid="marketplace-live-view-sheet-summary"',
    'data-testid="marketplace-progress-panel"',
], 'live view section');

const inputSection = read('components/marketplace/popup-sections/feature-popup-input-section.tsx');
includesAll(inputSection, [
    'data-testid="marketplace-popup-project-name"',
    'data-testid="marketplace-popup-template-id"',
    'data-testid="marketplace-popup-prompt"',
    'data-testid="marketplace-popup-photo-upload"',
    'data-testid="marketplace-popup-final-enabled"',
    'data-testid="marketplace-popup-submit"',
], 'input section');
assert.ok(inputSection.includes('aria-label={props.meta.templateLabel}'), 'input section should expose template aria label');

const stateSection = read('components/marketplace/popup-sections/feature-popup-state-section.tsx');
includesAll(stateSection, [
    'data-testid="marketplace-state-flow"',
    'data-testid="marketplace-progress-milestones"',
    'completed_preview_only',
    "props.popupState === 'failed'",
], 'state section');

const outputSection = read('components/marketplace/popup-sections/feature-popup-output-section.tsx');
includesAll(outputSection, [
    "mode === 'image'",
    "mode === 'music'",
    "mode === 'document'",
    "mode === 'video'",
    "mode === 'spreadsheet'",
    'Track Structure',
    'Outline',
    'Scene Cards',
    'Spreadsheet Downloads',
    'data-testid="marketplace-preview-artifact-card"',
    'data-testid="marketplace-final-artifact-card"',
], 'output section');

console.log('marketplace popup section contract tests passed');
