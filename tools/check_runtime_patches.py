# SPDX-License-Identifier: GPL-3.0-or-later
"""Replay every locked runtime patch on fresh pinned files in a private directory."""
import datetime
import argparse
import json
import re
import subprocess
from pathlib import Path


def main(prepare=False):
    root=Path(__file__).resolve().parents[1]
    lock=json.loads((root/'config/runtime.lock.json').read_text())
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')
    replay=root/'local/analysis'/('runtime-patch-replay-'+stamp)
    evidence=[]
    pending=[]
    for name,vendor,revision,patches in (
        ('core',root/'local/vendor/ModernGekko/vendor/dolphin',lock['recompcore_commit'],lock['patches']),
        ('runtime',root/'local/vendor/ModernGekko',lock['commit'],lock['runtime_patches'])):
        target=replay/name
        affected=set()
        for patch in patches:
            affected.update(re.findall(r'^\+\+\+ b/([^\r\n\t]+)',(root/patch).read_text(encoding='utf-8'),re.M))
        for relative in affected:
            destination=(target/relative).resolve()
            destination.relative_to(target.resolve())
            destination.parent.mkdir(parents=True,exist_ok=True)
            destination.write_bytes(subprocess.check_output(['git','-C',str(vendor),'show',revision+':'+relative]))
        recognized={p:{(target/p).read_text(encoding='utf-8')} for p in affected}
        for patch in patches:
            command=['git','-C',str(root),'apply','--directory='+target.relative_to(root).as_posix(),str(root/patch)]
            subprocess.run(command[:4]+['--check']+command[4:],check=True,capture_output=True)
            subprocess.run(command,check=True,capture_output=True)
            for p in affected:
                recognized[p].add((target/p).read_text(encoding='utf-8'))
        differences=[p for p in sorted(affected) if (target/p).read_text(encoding='utf-8')!=(vendor/p).read_text(encoding='utf-8')]
        if differences and not prepare:
            raise AssertionError('Replay differs from compiled source: '+repr(differences))
        for p in differences:
            if (vendor/p).read_text(encoding='utf-8') not in recognized[p]:
                raise AssertionError('Refusing to overwrite unrecognized source changes: '+str(vendor/p))
            pending.append((vendor/p, (target/p).read_bytes()))
        evidence.append({'component':name,'revision':revision,'patches':patches,'files_compared':len(affected),'matches_current_source':True})
    # Validate both checkouts before changing any file. Only known patch-prefix states qualify.
    for destination, data in pending:
        destination.write_bytes(data)
    (replay/'result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    print(f'PASS complete patch replay: {len(lock["patches"])+len(lock["runtime_patches"])} patches; {replay}')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true',help='Advance known patch-prefix sources to the full locked series; refuse other edits')
    main(parser.parse_args().prepare)
