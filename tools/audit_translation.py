"""Compare local dtk analysis with generated C; summarize unresolved CPU paths."""
import argparse
import collections
import csv
import json
import re
from pathlib import Path


def dtk_functions(directory):
    result = []
    header = re.compile(r'^#\s+\S+:0x[0-9A-Fa-f]+\s+\|\s+(0x[0-9A-Fa-f]+)\s+\|\s+size:\s+(0x[0-9A-Fa-f]+)')
    definition = re.compile(r'^\.fn\s+([^,\s]+)')
    for path in sorted(directory.glob('*.s')):
        pending = None
        for line in path.read_text(encoding='utf-8').splitlines():
            match = header.match(line)
            if match:
                pending = dict(address=match[1], size=int(match[2], 16), source=path.name)
            match = definition.match(line)
            if match:
                if pending is None:
                    raise ValueError(f'Function without address/size metadata: {path}: {line}')
                result.append(dict(name=match[1], **pending))
                pending = None
    if not result:
        raise ValueError(f'No dtk function definitions in {directory}')
    addresses = [int(f['address'], 16) for f in result]
    if len(set(addresses)) != len(addresses):
        raise ValueError(f'Duplicate dtk function addresses in {directory}')
    return result


def audit_c(directory):
    result, bytes_count = [], 0
    calls = re.compile(r'ppc_fallback_instruction\(ctx,\s*(0x[0-9A-Fa-f]+)u?,\s*(0x[0-9A-Fa-f]+)u?\)')
    host_calls = re.compile(r'ppc_host_call\(ctx,\s*(0x[0-9A-Fa-f]+)u?\)')
    host_sites = set()
    paths = sorted(directory.glob('*.c'))
    for path in paths:
        text = path.read_text(encoding='utf-8')
        bytes_count += path.stat().st_size
        for raw, address in calls.findall(text):
            raw_int = int(raw, 16)
            result.append(dict(address=address, raw=raw, primary_opcode=raw_int >> 26,
                               extended_opcode=(raw_int >> 1) & 1023, chunk=path.name))
        host_sites.update(host_calls.findall(text))
    op_names = {54: 'dcbst', 86: 'dcbf', 470: 'dcbi', 982: 'icbi',
                339: 'mfspr', 467: 'mtspr', 371: 'mftb'}
    operations = collections.Counter(
        op_names.get(r['extended_opcode'], f'xo_{r["extended_opcode"]}')
        if r['primary_opcode'] == 31 else f'op_{r["primary_opcode"]}' for r in result)
    return dict(chunks=len(paths), generated_chunk_bytes=bytes_count,
                fallback_calls=len(result), unique_fallback_sites=len({r['address'] for r in result}),
                fallback_operations=dict(operations),
                fallback_raw_counts=dict(collections.Counter(r['raw'] for r in result)),
                unique_host_hook_sites=len(host_sites)), result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    output = root / 'local/analysis'
    output.mkdir(parents=True, exist_ok=True)
    summary = {}
    for module, asm, generated in (
        ('dol', root / 'local/analysis/dtk-split/asm', root / 'local/generated/dolrecomp/dol/main_chunks'),
        ('rel', root / 'local/analysis/dtk-split/ovl_main/asm', root / 'local/generated/dolrecomp/rel/ovl_main_chunks'),
    ):
        functions = dtk_functions(asm)
        code, fallback = audit_c(generated)
        summary[module] = dict(dtk_function_count=len(functions),
                               dtk_function_bytes=sum(f['size'] for f in functions), **code)
        with (output / f'{module}-functions.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['name', 'address', 'size', 'source'])
            writer.writeheader()
            writer.writerows(functions)
        with (output / f'{module}-fallbacks.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=['address', 'raw', 'primary_opcode', 'extended_opcode', 'chunk'])
            writer.writeheader()
            writer.writerows(fallback)
    summary['note'] = 'dtk function boundaries are heuristic. DolRecomp chunks are fixed-size compilation units, not functions. Zero unknown opcodes does not mean zero fallback calls.'
    (output / 'translation-audit.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: {k: v for k, v in value.items() if k != 'fallback_raw_counts'}
                      for key, value in summary.items() if isinstance(value, dict)}, indent=2))


if __name__ == '__main__':
    main()
