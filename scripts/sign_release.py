#!/usr/bin/env python3
"""Sign release checksums with the creator's private key; never bundle the key."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from version import VERSION, CREATOR, COAUTHOR


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--key', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    output = args.output.resolve()
    key = args.key.resolve()
    if ROOT == key or ROOT in key.parents or output in key.parents:
        raise SystemExit('The private key must be kept separate from the project and the distribution.')
    public = subprocess.check_output(['openssl', 'pkey', '-in', str(key), '-pubout'])
    if public != (ROOT / 'signing/droiddesk-public.pem').read_bytes():
        raise SystemExit('The key does not match the public key registered in the project.')
    files = [output / f'droiddesk_{VERSION}_all.deb', output / f'droiddesk-{VERSION}-linux.tar.gz']
    if not all(p.is_file() for p in files):
        raise SystemExit('Build both packages before signing.')
    provenance = dict(project='DroidDesk', version=VERSION, creator=CREATOR, coauthor=COAUTHOR,
                      authors_sha256=hashlib.sha256((ROOT / 'AUTHORS.md').read_bytes()).hexdigest(),
                      public_key_sha256=hashlib.sha256(public).hexdigest(),
                      artifacts={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
    record = output / 'PROVENANCE.json'
    record.write_text(json.dumps(provenance, indent=2, ensure_ascii=False) + '\n')
    public_file = output / 'droiddesk-public.pem'
    public_file.write_bytes(public)
    files += [record, public_file]
    checksums = output / 'SHA256SUMS'
    checksums.write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.name + '\n' for p in files))
    signature = output / 'SHA256SUMS.sig'
    subprocess.run(['openssl', 'pkeyutl', '-sign', '-inkey', str(key), '-rawin', '-in', str(checksums), '-out', str(signature)], check=True)
    subprocess.run(['openssl', 'pkeyutl', '-verify', '-pubin', '-inkey', str(public_file), '-rawin', '-in', str(checksums), '-sigfile', str(signature)], check=True)
    subprocess.run(['sha256sum', '-c', 'SHA256SUMS'], cwd=output, check=True)
    print('Signed packages. Private key not included.')


if __name__ == '__main__':
    main()
