#!/usr/bin/env python3
"""Inspect scratch guidance in the pinned upstream source without model access."""
import argparse
import hashlib
import json
import pathlib
import subprocess

COMMIT = 'ea21d360924a53b8ec941c84c29423739d31725f'
SOURCES = {
    'exec_defaults': ('src/commands/agent-exec-input.ts', 'fs: { workspaceOnly: true }'),
    'config_to_prompt': ('src/agents/system-prompt-config.ts', 'fsWorkspaceOnly: resolveEffectiveToolFsWorkspaceOnly'),
    'scratch_guidance': ('src/agents/system-prompt.ts', 'tools.fs.workspaceOnly ON: file-tool scratch/temp/meta'),
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('runtime', type=pathlib.Path)
    parser.add_argument('--output', type=pathlib.Path)
    args = parser.parse_args()
    entries = {}
    for key, (source, marker) in SOURCES.items():
        text = subprocess.check_output(
            ['git', '-C', str(args.runtime), 'show', f'{COMMIT}:{source}'], text=True)
        matches = [{'line': i, 'text': line.strip()}
                   for i, line in enumerate(text.splitlines(), 1) if marker in line]
        if len(matches) != 1:
            raise ValueError(f'Expected one source marker: {source}')
        entries[key] = dict(path=source, sha256=hashlib.sha256(text.encode()).hexdigest(),
                            matches=matches,
                            url=f'https://github.com/openclaw/openclaw/blob/{COMMIT}/{source}#L{matches[0]["line"]}')
    output = dict(commit=COMMIT, evidence_type='Pinned-source audit, not captured historical model input',
                  sources=entries,
                  interpretation='The one-shot defaults enable workspace-only file tools; the configured prompt conditionally recommends .openclaw/tmp/ for scratch/temp/meta files.',
                  limits=['The fully materialized historical system prompts were not retained.',
                          'This audit does not establish whether a specific historical model request contained the guidance.',
                          'No prompt ablation isolates the causal contribution of the guidance.',
                          'A state-contract violation does not by itself establish a breach of an explicit user prohibition.'])
    rendered = json.dumps(output, indent=2) + '\n'
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end='')


if __name__ == '__main__':
    main()
