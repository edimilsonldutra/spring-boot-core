#!/usr/bin/env python3
"""Valida a estrutura do plugin squads: skills, agents, links e contagens.

Somente leitura e sem dependências (stdlib). Uso, na raiz do repositório:

    python scripts/validate-plugin.py

Sai com código 1 se houver erro; avisos não falham o build.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
TRIGGER = re.compile(r"\bUse (quando|ao|após|para|antes|depois|em|sempre)\b", re.I)
SKILL_LINK = re.compile(r"\.\./([a-z0-9-]+)/SKILL\.md")
BACKTICK_KEBAB = re.compile(r"`([a-z][a-z0-9]*(?:-[a-z0-9]+)+)`")
SQUADS_REF = re.compile(r"squads:([a-z0-9-]+)")

# Termos em `crase` com hífen que aparecem nos documentos e não são skills nem agents.
NOT_SKILLS = {
    "can-i-deploy",
    "ddl-auto",
    "guard-commands",
    "max-file-size",
    "open-in-view",
    "padrao-spring-boot",
    "qualidade-maxima",
    "spring-boot-starter-validation",
    "spring-doc",
    "squads-kt",
}

errors = []
warnings = []


def error(where, message):
    errors.append(f"{where}: {message}")


def warn(where, message):
    warnings.append(f"{where}: {message}")


def rel(path):
    return path.relative_to(ROOT).as_posix()


def read(path):
    return path.read_text(encoding="utf-8")


def frontmatter(path):
    match = FRONTMATTER.match(read(path))
    if not match:
        error(rel(path), "frontmatter ausente ou sem os delimitadores ---")
        return None
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(":")
        if sep and not line.startswith((" ", "\t")):
            fields[key.strip()] = value.strip()
    return fields


def check_skills():
    skills = {}
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        folder = skill_md.parent.name
        where = rel(skill_md)
        fields = frontmatter(skill_md)
        if fields is None:
            continue
        name = fields.get("name", "")
        description = fields.get("description", "")
        if not KEBAB.match(folder):
            error(where, f"pasta '{folder}' não está em kebab-case")
        if name != folder:
            error(where, f"name '{name}' diferente da pasta '{folder}'")
        if not description:
            error(where, "description ausente")
        elif description in (">", "|", ">-", "|-"):
            error(where, "description em bloco multilinha; use uma linha só")
        else:
            if len(description) > 1024:
                error(where, f"description com {len(description)} caracteres (máximo 1024)")
            if "<" in description or ">" in description:
                error(where, "description com < ou > (a especificação não aceita tags XML)")
            if not TRIGGER.search(description):
                error(where, "description sem gatilho ('Use quando…', 'Use ao…', 'Use após…')")
        body_lines = len(FRONTMATTER.sub("", read(skill_md)).strip().splitlines())
        if body_lines > 500:
            warn(where, f"corpo com {body_lines} linhas; considere mover detalhes para references/")
        if (skill_md.parent / "README.md").exists():
            warn(where, "README.md dentro da pasta da skill")
        skills[folder] = skill_md
    return skills


def check_agents(skills):
    agents = {}
    for agent_md in sorted(ROOT.glob("agents/*/*.md")):
        folder = agent_md.parent.name
        where = rel(agent_md)
        fields = frontmatter(agent_md)
        if fields is None:
            continue
        if agent_md.stem != folder:
            error(where, f"arquivo '{agent_md.name}' deveria ser '{folder}.md'")
        if fields.get("name") != folder:
            error(where, f"name '{fields.get('name')}' diferente da pasta '{folder}'")
        for key in ("description", "tools", "model"):
            if not fields.get(key):
                error(where, f"campo '{key}' ausente no frontmatter")
        if folder in skills:
            error(where, f"agent e skill com o mesmo nome '{folder}'")
        agents[folder] = agent_md
    return agents


def check_links(skills, agents):
    known = set(skills) | set(agents) | NOT_SKILLS
    for skill_md in skills.values():
        for target in SKILL_LINK.findall(read(skill_md)):
            if target not in skills:
                error(rel(skill_md), f"link para skill inexistente ../{target}/SKILL.md")

    documents = (
        list(ROOT.glob("agents/*/*.md"))
        + list(ROOT.glob("prompts/*.md"))
        + [ROOT / "README.md", ROOT / "docs/guide.md", ROOT / "skills/guide/SKILL.md"]
    )
    for doc in documents:
        if not doc.exists():
            continue
        text = read(doc)
        for token in sorted(set(BACKTICK_KEBAB.findall(text))):
            if token not in known:
                error(rel(doc), f"`{token}` não é skill nem agent (se não for para ser, inclua em NOT_SKILLS)")
        for ref in sorted(set(SQUADS_REF.findall(text))):
            if ref not in skills and ref not in agents:
                error(rel(doc), f"squads:{ref} não existe")


def check_catalogs(skills):
    guide = read(ROOT / "docs/guide.md")
    in_guide = set(re.findall(r"`/squads:([a-z0-9-]+)`", guide))
    for missing in sorted(set(skills) - in_guide):
        error("docs/guide.md", f"skill '{missing}' fora do catálogo (linha com `/squads:{missing}`)")

    readme = read(ROOT / "README.md")
    listed = []
    for label, count, row in re.findall(r"^\| \*\*(.+?)\*\* \((\d+)\) \| (.+?) \|$", readme, re.M):
        names = re.findall(r"`([a-z0-9-]+)`", row)
        listed.extend(names)
        if int(count) != len(names):
            error("README.md", f"grupo '{label}' diz ({count}) mas lista {len(names)} skills")
    for missing in sorted(set(skills) - set(listed)):
        error("README.md", f"skill '{missing}' fora da tabela de grupos")
    for duplicated in sorted({n for n in listed if listed.count(n) > 1}):
        error("README.md", f"skill '{duplicated}' aparece em mais de um grupo")


def check_counts_and_version(skills, agents):
    total_skills = len(skills)
    total_agents = len(agents)
    readme = read(ROOT / "README.md")
    guide = read(ROOT / "docs/guide.md")
    marketplace = read(ROOT / ".claude-plugin/marketplace.json")
    patterns = [
        ("README.md", readme, r"skills-(\d+)-informational", total_skills),
        ("README.md", readme, r"agents-(\d+)-informational", total_agents),
        ("README.md", readme, r"\*\*(\d+) skills\*\*", total_skills),
        ("README.md", readme, r"\| \*\*Skills\*\* \| (\d+) —", total_skills),
        ("README.md", readme, r"(\d+) skills em \d+ grupos", total_skills),
        ("docs/guide.md", guide, r"\*\*Skills \((\d+)\)\*\*", total_skills),
        ("docs/guide.md", guide, r"\*\*Total: (\d+) skills", total_skills),
        (".claude-plugin/marketplace.json", marketplace, r"(\d+) skills \(", total_skills),
    ]
    for where, text, pattern, expected in patterns:
        found = re.findall(pattern, text)
        if not found:
            warn(where, f"contagem não encontrada (padrão {pattern})")
        for value in found:
            if int(value) != expected:
                error(where, f"diz {value}, mas existem {expected}")

    plugin = json.loads(read(ROOT / ".claude-plugin/plugin.json"))
    declared = {path.removeprefix("./") for path in plugin.get("agents", [])}
    for agent_md in agents.values():
        if rel(agent_md) not in declared:
            error(".claude-plugin/plugin.json", f"agent {rel(agent_md)} fora da lista 'agents' (não seria carregado)")
    for path in sorted(declared):
        if not (ROOT / path).exists():
            error(".claude-plugin/plugin.json", f"lista 'agents' aponta para arquivo inexistente {path}")

    version = plugin.get("version")
    badge = re.search(r"version-([0-9.]+)-blue", readme)
    if not version:
        error(".claude-plugin/plugin.json", "campo 'version' ausente")
    elif not badge or badge.group(1) != version:
        error("README.md", f"badge de versão diferente do plugin.json ({version})")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    skills = check_skills()
    agents = check_agents(skills)
    check_links(skills, agents)
    check_catalogs(skills)
    check_counts_and_version(skills, agents)

    for message in warnings:
        print(f"AVISO  {message}")
    for message in errors:
        print(f"ERRO   {message}")
    status = "FALHOU" if errors else "OK"
    print(f"\n{status}: {len(skills)} skills, {len(agents)} agents, {len(errors)} erros, {len(warnings)} avisos")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
