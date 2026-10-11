import re
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "deploy-to-box.sh"


def test_printed_deploy_commands_include_sha_flag():
    """
    Régression CC-56 : --sha est désormais obligatoire sur deploy-to-box.sh.
    Toute commande `./scripts/deploy-to-box.sh ...` que le script affiche à
    l'utilisateur (rollback, republication, etc.) doit donc inclure --sha,
    sinon elle échoue immédiatement si l'utilisateur la copie-colle telle
    quelle (cf. PR #235 / revue Codex).
    """
    lines = SCRIPT_PATH.read_text(encoding="utf-8").splitlines()

    offending = []
    for lineno, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if "deploy-to-box.sh" not in line:
            continue
        if not re.search(r"\b(echo|printf)\b", line):
            continue
        if "--sha" not in line:
            offending.append((lineno, line))

    assert not offending, (
        "Commande(s) deploy-to-box.sh affichée(s) sans --sha, incompatible "
        f"avec le garde-fou --sha obligatoire (CC-56) : {offending}"
    )
