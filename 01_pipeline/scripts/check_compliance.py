#!/usr/bin/env python3
"""CareHub infrastructure compliance gate.

Rules intentionally kept small, explicit and blocking for the exam.
"""
from __future__ import annotations
import sys
from pathlib import Path
import yaml

CRITICAL = {'app', 'db', 'proxy'}


def fail(messages: list[str]) -> int:
    print('COMPLIANCE: FAIL')
    for message in messages:
        print(f' - {message}')
    return 1


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_compliance.py <compose.yml>', file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    data = yaml.safe_load(path.read_text(encoding='utf-8')) or {}
    services = data.get('services', {})
    errors: list[str] = []

    for name, service in services.items():
        image = str(service.get('image', ''))
        if image.endswith(':latest') or image == 'latest':
            errors.append(f'{name}: tag flottant latest interdit')
        if service.get('privileged') is True:
            errors.append(f'{name}: privileged=true interdit')
        if service.get('network_mode') == 'host':
            errors.append(f'{name}: network_mode=host interdit')
        if name in CRITICAL and 'healthcheck' not in service:
            errors.append(f'{name}: healthcheck obligatoire')

        has_cpu = 'cpus' in service
        has_mem = 'mem_limit' in service
        if name in CRITICAL and not (has_cpu and has_mem):
            errors.append(f'{name}: limites cpus et mem_limit obligatoires')

        env = service.get('environment', {})
        if isinstance(env, dict):
            for key, value in env.items():
                if any(token in key.upper() for token in ('PASSWORD', 'SECRET', 'TOKEN')):
                    text = '' if value is None else str(value)
                    if text and not text.startswith('${'):
                        errors.append(f'{name}: valeur sensible {key} doit venir d une variable/secrète')

    if not services:
        errors.append('aucun service défini')
    if errors:
        return fail(errors)
    print(f'COMPLIANCE: PASS - {len(services)} services contrôlés dans {path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
