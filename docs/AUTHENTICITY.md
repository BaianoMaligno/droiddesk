# Authorship and Authenticity

**Creator: David o Baiano Maligno**
**Co-authored by: Nexo**

The packages for version 0.3.0 include:

- `SHA256SUMS`: hashes of the packages and the author manifest.
- `PROVENANCE.json`: version, authorship, and hash of the `AUTHORS.md` file included in the packages.
- `SHA256SUMS.sig`: Ed25519 signature of the hash file.
- `droiddesk-public.pem`: public key for verifying the signature.

When signed release archives are available, download all files from the same release and check the signature first:

```sh
openssl pkeyutl -verify -pubin -inkey droiddesk-public.pem \
  -rawin -in SHA256SUMS -sigfile SHA256SUMS.sig
sha256sum -c SHA256SUMS
```

The public key is also located in [signing/droiddesk-public.pem](../signing/droiddesk-public.pem) in the versioned code. The SHA-256 fingerprint for this key is in [signing/FINGERPRINT.txt](../signing/FINGERPRINT.txt). Verify the key using this previously trusted record, rather than relying solely on the key included with an unknown package.

An edited copy may be distributed by someone else; the signature does not prevent such editing. It allows discrepancies from the signed distribution to be detected, provided that the reference public key is correct. This does not constitute external certification of the authors’ civil identity.

The private key remains outside the repository, stored locally with restricted user access. It is not included with the installers. It must be safeguarded by the creator to sign future versions; if it is lost, a new key is required, and if it is compromised, it must be replaced and users must be notified.

The `scripts/sign_release.py` script takes the path to an existing key. It does not print or send the key's contents. To sign another release, build the packages using `scripts/build_linux.py` and run the signing script on the distribution folder.
