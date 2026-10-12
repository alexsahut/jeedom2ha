#!/usr/bin/env python3
"""Construction et validation du paquet Market épuré de jeedom2ha (story A2).

Sous-commandes :
  build  <sha> <outdir> [--tarball F] [--with-retained] [--repo DIR]
  check  <dir> [--release-tree]

Stdlib uniquement (Python >= 3.8) : ce fichier est aussi conservé sur beta/stable
(option 1) pour que le workflow de validation y tourne sans dépendance.
"""
import argparse
import fnmatch
import gzip
import io
import os
import subprocess
import sys
import tarfile

MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)), "manifest.txt")


def load_manifest(path=MANIFEST):
    data = {"include": [], "exclude": [], "rules": [], "forbid": [], "require": [], "retain": []}
    with open(path, encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split(None, 1)
            if len(parts) != 2 or parts[0] not in ("include", "exclude", "forbid", "require", "retain"):
                raise ValueError("%s:%d: ligne invalide: %r" % (path, lineno, line))
            kind, pattern = parts
            data[kind].append(pattern)
            if kind in ("include", "exclude"):
                data["rules"].append((kind, pattern))
    return data


def matches(pattern, relpath):
    """Vrai si le motif désigne ce fichier (chemin relatif, séparateur '/')."""
    comps = relpath.split("/")
    if pattern.endswith("/"):
        pat = pattern[:-1]
        dirs = comps[:-1]
        if "/" in pat:
            n = len(pat.split("/"))
            return "/".join(dirs[:n]) == pat
        return any(fnmatch.fnmatchcase(d, pat) for d in dirs)
    if "/" in pattern:
        return fnmatch.fnmatchcase(relpath, pattern)
    return fnmatch.fnmatchcase(comps[-1], pattern)


def is_included(rules, relpath):
    for kind, pattern in rules:
        if matches(pattern, relpath):
            return kind == "include"
    return True


def is_retained(manifest, relpath):
    return relpath in manifest["retain"]


def build(sha, outdir, repo=".", with_retained=False, tarball=None, manifest=None):
    manifest = manifest or load_manifest()
    os.makedirs(outdir, exist_ok=True)
    if os.listdir(outdir):
        raise SystemExit("ERREUR: le dossier de sortie n'est pas vide: %s" % outdir)
    commit_time = int(subprocess.check_output(
        ["git", "-C", repo, "show", "-s", "--format=%ct", sha + "^{commit}"]).decode().strip())
    archive = subprocess.check_output(["git", "-C", repo, "archive", "--format=tar", sha])
    written = []
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        for m in tar:
            if not (m.isfile() or m.issym()):
                continue
            rel = m.name
            keep = is_included(manifest["rules"], rel) or (
                with_retained and is_retained(manifest, rel))
            if not keep:
                continue
            dest = os.path.join(outdir, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if m.issym():
                os.symlink(m.linkname, dest)
            else:
                with open(dest, "wb") as out:
                    out.write(tar.extractfile(m).read())
                os.chmod(dest, 0o755 if m.mode & 0o111 else 0o644)
                os.utime(dest, (commit_time, commit_time))
            written.append(rel)
    if with_retained:
        missing = [r for r in manifest["retain"] if r not in written]
        if missing:
            raise SystemExit("ERREUR: fichiers 'retain' absents du SHA source %s: %s"
                             % (sha, ", ".join(missing)))
    if tarball:
        write_tarball(outdir, tarball, commit_time)
    return sorted(written)


def write_tarball(outdir, tarball, mtime):
    """tar.gz déterministe : ordre trié, uid/gid 0, mtime fixe, en-tête gzip sans date."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for rel in list_files(outdir):
            full = os.path.join(outdir, rel)
            info = tar.gettarinfo(full, arcname=rel)
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = mtime
            if info.isreg():
                with open(full, "rb") as fh:
                    tar.addfile(info, fh)
            else:
                tar.addfile(info)
    with open(tarball, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(buf.getvalue())


def list_files(root):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames + [d for d in dirnames if os.path.islink(os.path.join(dirpath, d))]):
            full = os.path.join(dirpath, name)
            out.append(os.path.relpath(full, root).replace(os.sep, "/"))
    return sorted(out)


def check(root, release_tree=False, manifest=None):
    """Retourne la liste des violations (vide = conforme)."""
    manifest = manifest or load_manifest()
    files = list_files(root)
    retained = set(manifest["retain"]) if release_tree else set()
    violations = []
    for rel in files:
        if rel in retained:
            continue
        if not is_included(manifest["rules"], rel):
            violations.append("fichier exclu par les règles include/exclude mais présent: " + rel)
        for pattern in manifest["forbid"]:
            if matches(pattern, rel):
                violations.append("fichier interdit (forbid %s) présent: %s" % (pattern, rel))
    for pattern in manifest["require"]:
        if pattern.endswith("/"):
            ok = any(matches(pattern, f) for f in files)
        else:
            ok = pattern in files
        if not ok:
            violations.append("fichier requis absent: " + pattern)
    for rel in retained:
        if rel not in files:
            violations.append("fichier 'retain' absent de l'arbre de release: " + rel)
    return sorted(set(violations))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("sha")
    b.add_argument("outdir")
    b.add_argument("--repo", default=".")
    b.add_argument("--tarball")
    b.add_argument("--with-retained", action="store_true")
    c = sub.add_parser("check")
    c.add_argument("dir")
    c.add_argument("--release-tree", action="store_true")
    args = ap.parse_args(argv)
    if args.cmd == "build":
        files = build(args.sha, args.outdir, args.repo, args.with_retained, args.tarball)
        print("paquet épuré: %d fichiers -> %s" % (len(files), args.outdir))
        return 0
    violations = check(args.dir, args.release_tree)
    if violations:
        for v in violations:
            print("VIOLATION: " + v, file=sys.stderr)
        return 1
    print("manifeste respecté: %s" % args.dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
