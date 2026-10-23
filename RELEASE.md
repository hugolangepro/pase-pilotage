# Releasing PASE

PASE is published to PyPI as **`pase-agrivoltaics`** (the import package stays
`pase`). Releases are **semi-automated**: a maintainer drives the changelog,
merge, and tag; CI builds and publishes.

The version is derived from the git tag by **setuptools-scm** — there is no
version string to bump by hand. A clean checkout sitting exactly on tag
`vX.Y.Z` builds as `X.Y.Z`; anything else builds as a `.devN+g<hash>`
pre-release (which PyPI refuses, so dev builds can never be published by
accident).

---

## Versioning policy — choosing the number

setuptools-scm derives the version *string* from the tag, but **you** choose the
tag, so you decide MAJOR.MINOR.PATCH. PASE follows [SemVer](https://semver.org/):

- **MAJOR** — a breaking change (see below).
- **MINOR** — backward-compatible new functionality.
- **PATCH** — backward-compatible bug fixes.

**PASE's public contract** — what a change can break — is broader than a plain
library's importable API. It is:

1. the **Python API** users import (classes, functions, signatures);
2. the **input-file schemas** (YAML/config formats — the main user interface);
3. the **supported runtime and dependencies** users rely on (e.g. the minimum
   Python version);
4. the **default behaviour / results** produced when the user changes nothing.

**The test for "breaking":** a user who does exactly what they did before now
gets an error or a *materially different result*, without changing their own code
or inputs. If yes, it is breaking → **MAJOR**.

Examples:

- **Breaking (MAJOR):** removing/renaming a public class or function; changing an
  input-file layout so existing files no longer load; dropping a supported Python
  version; changing a default so unchanged runs produce different results.
- **Not breaking (MINOR/PATCH):** adding an optional feature or parameter with a
  safe default; fixing a bug so results become *correct* (call it out in the
  changelog, but it does not by itself force a MAJOR); internal refactors with
  identical public behaviour.

When in doubt, prefer the higher bump and describe the change in the CHANGELOG:
under-signalling a breaking change erodes user trust more than an "extra" major
does. (This is why the catch-up release is `2.0.0`, not `1.4.0` — see below.)

---

## One-time setup (project Owner, in the GitLab UI)

Do this once before the first release. It cannot be done from the repo.

1. **PyPI + TestPyPI accounts.** Create accounts on <https://pypi.org> and
   <https://test.pypi.org>. The first upload of `pase-agrivoltaics` claims the
   name for the lab.
2. **API tokens as CI/CD variables** (Settings → CI/CD → Variables). Add both as
   **Protected** and **Masked**:
   - `PYPI_API_TOKEN` — a PyPI API token (scope it to the project once it exists).
   - `TESTPYPI_API_TOKEN` — a TestPyPI API token.
   > Trusted Publishing (OIDC) is **not** available: PyPI only trusts the
   > `gitlab.com` issuer, and PASE is on self-hosted `gitlab.uliege.be`. Hence
   > token auth.
3. **Protect the release tags** (Settings → Repository → Protected tags): add the
   wildcard `v*` so only maintainers can create release tags and the protected
   tokens are exposed to those pipelines.

---

## What CI does

On a pushed tag matching `vX.Y.Z`:

1. `test_release` — runs the suite with `-m "not network"` (skips the live-PVGIS
   tests so a network hiccup can't block a release).
2. `build` — builds the sdist + wheel and runs `twine check`.
3. `publish_testpypi` — **manual** (click ▶ in the pipeline) dry-run upload to
   TestPyPI. Non-blocking.
4. `publish_pypi` — uploads to PyPI. **Only on final tags** (`vX.Y.Z` with no
   suffix); `rc`/pre-release tags stop at TestPyPI.

`build` also runs on the default branch so packaging breakage is caught early.

---

## Release checklist

The release runs through the normal GitLab workflow: **open an issue, then create
the branch and merge request from it in the GitLab UI** (favour the UI over the
CLI throughout).

1. **Prep `develop`.** Ensure all changes are on `develop` and its pipeline is green.
2. **Open a release issue** — e.g. `[release] vX.Y.Z` — as the anchor for the
   branch and MR.
3. **Create the release branch + MR from the issue (GitLab UI).** From the issue,
   use *Create merge request*; set the branch **off `develop`**, name it
   `release-vX.Y.Z`, and **target `main`**.
4. **Finalize the changelog on the release branch.** In `CHANGELOG.md`, retitle
   `## [Unreleased]` → `## [X.Y.Z] - YYYY-MM-DD`, resolve any "Needs human triage"
   items, and add a fresh empty `## [Unreleased]` above it. Commit to
   `release-vX.Y.Z` (so it travels to `main` and, later, back to `develop`).
5. **Merge the MR into `main`** once it has one Owner approval and a green pipeline. **Do not delete the release branch yet !**
6. **Tag on `main` (GitLab UI).** Repository → Tags → *New tag*: `vX.Y.Z`, created
   from `main` (the merge commit). This fires the tag pipeline. The tree is clean
   at the tag, so setuptools-scm emits `X.Y.Z` (no `.dev`/`+`).
7. **TestPyPI dry-run.** In the tag pipeline, run the manual `publish_testpypi`
   job — recommended whenever anything about packaging changed.
8. **Publish.** `publish_pypi` runs automatically on the final tag. Confirm at
   <https://pypi.org/project/pase-agrivoltaics/> and in a clean venv:
   ```bash
   pip install pase-agrivoltaics
   python -c "import pase; print(pase.__version__)"
   ```
9. **Publish the GitLab Release** for the tag, pasting the `CHANGELOG.md` section
   as the release notes.
10. **Back-merge the release branch into `develop`.** Open an MR
    `release-vX.Y.Z → develop` (GitLab UI) and merge it, so the release commits
    (notably the changelog retitle) land on `develop`. This MR can delete the release branch after the merge.

---

## First release — v2.0.0 (catch-up)

`v2.0.0` is the first release on this pipeline and clears the `v1.3.0..develop`
backlog (see the `[Unreleased]` entry in `CHANGELOG.md`). The major bump follows
SemVer: the backlog carries breaking changes since v1.3.0 — the Python-floor bump
(#256), the GRASSIM input-layout change (#199), the default sky-model change
(#117), and the `MultiBlock_PASE` removal (#184). `main` is far behind `develop`;
we do **not** reconstruct the intermediate releases — a single
`release-v2.0.0 → main → tag v2.0.0` (via the checklist above) brings `main`
current in one clean, auditable step and proves the pipeline end to end.

The pipeline has already been smoke-tested end to end with throwaway `v1.4.0rc*`
tags that built and uploaded to TestPyPI. To repeat a dry run for a future
release, create a throwaway pre-release tag in the UI (Repository → Tags → *New
tag*, e.g. `vX.Y.Zrc1`), run the manual `publish_testpypi` job, then delete the
tag in the UI. `rc` tags go to TestPyPI only, never PyPI.
