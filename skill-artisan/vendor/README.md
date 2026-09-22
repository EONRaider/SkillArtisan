# Vendored dependencies

Third-party code shipped with the plugin so that `scripts/validate.py` works
with no network access and no npm install. Nothing here is written or
maintained by this project; it is a verbatim copy of what the npm registry
publishes, and it should stay that way so the integrity hashes below keep
verifying.

## Why vendored rather than fetched

`validate.py` previously fell back to `npx --yes skills-ref@0.1.5` whenever
`skills-ref` wasn't already installed. That runs code downloaded from a
public registry on the author's machine, at validate time, on every run. The
version pin bounds *which* release gets executed, but pinning is not
reviewing — nothing about it makes the downloaded code vetted, and the fetch
silently fails in any environment without egress (CI runners on a locked-down
network, offline work, sandboxed sessions), turning validation into a
no-result rather than a pass or a fail.

Vendoring the same release removes both problems: the bytes are in the repo,
reviewable in a diff and pinned by commit, and validation behaves the same
everywhere. `validate.py` still prefers a `skills-ref` the author installed
themselves, so a deliberate local choice wins over this copy. The registry
fetch remains available behind `SKILLS_REF_ALLOW_NPX_FETCH=1` for anyone who
wants it, and is off by default.

## Contents and provenance

Fetched from `https://registry.npmjs.org`, unpacked unmodified. Runtime
dependencies were installed with `npm install --omit=dev --ignore-scripts`,
so no devDependency toolchain and no install script ships here. The npm
bookkeeping files (`.package-lock.json`, `node_modules/.bin/`) were removed;
they are generated state, not package content, and `validate.py` invokes
`node vendor/skills-ref/dist/cli.js` directly rather than through a bin shim.

| Package | Version | `dist.integrity` from the registry |
| --- | --- | --- |
| `skills-ref` | 0.1.5 | `sha512-C2vyZbUQqt3PXA9vcdUmJ0lwbH9jK19C9fwQjl/ICPy2e5bzV3CaropViakJCv+HLt/9zsgjZ/NLJ5xEri0jSA==` |
| `commander` | 12.1.0 | `sha512-Vw8qHK3bZM9y/P10u3Vib8o/DdkvA2OtPtZvD871QKjy74Wj1WSKFILMPRPSdUSx5RFK1arlJzEtA4PkFgnbuA==` |
| `js-yaml` | 4.3.2 | `sha512-SFNOvSJ+Dgf/9An904Yx+CgSlIPCkIpao4qo51lpee25TIRejdH3rhR4EZMGoNx3/TP3O+wzWuiTFl4sqbltzA==` |
| `argparse` | 2.0.1 | `sha512-8+9WqebbFzpX9OR+Wa6O29asIogeRMzcGtAINdpMHHyAg10f05aSFVBbcEqGf/PXw1EjAZ+q2/bEBg3DvurK3Q==` |

`commander` and `js-yaml` are `skills-ref`'s own declared runtime
dependencies; `argparse` is `js-yaml`'s. All four are needed for
`dist/cli.js` to start.

To re-verify that this directory still matches what the registry publishes:

```bash
curl -sO https://registry.npmjs.org/skills-ref/-/skills-ref-0.1.5.tgz
echo "sha512-$(openssl dgst -sha512 -binary skills-ref-0.1.5.tgz | openssl base64 -A)"
```

and compare the result against the table, then diff the unpacked `package/`
against `skills-ref/` (ignoring `node_modules/`, which is installed, not
shipped in the tarball). Repeat per package for the dependencies.

## Known upstream issue: `skills-ref`'s licence is self-contradictory

Reported here, not fixed — the vendored files are deliberately left byte for
byte as published, and correcting a third-party project's licensing is not
something a downstream copy can do.

`skills-ref@0.1.5` declares `"license": "MIT"` in its `package.json`, but the
`LICENSE` file it actually ships is the full text of the Apache License 2.0.
The two are different licences with materially different terms — Apache-2.0
carries an express patent grant and a notice/attribution requirement that MIT
does not. Anyone whose redistribution or compliance obligations turn on which
one applies should treat the discrepancy as unresolved and take it up with
`skills-ref`'s author rather than relying on either declaration.

This does not affect how the plugin uses the tool, and it is not a defect in
the validator's behaviour.

## A note on `js-yaml/lib/index_vite_proxy.tmp.mjs`

This file is present in the published `js-yaml@4.3.2` tarball and is kept
here for that reason: removing it would break byte-identity with the
registry, which is the whole point of the table above. Nothing in `js-yaml`'s
`exports` map or `skills-ref`'s import graph references it — it is a
re-export shim that looks like a build-tool artifact that made it into the
published `lib/` directory. It is inert.
