#!/usr/bin/env bash
# PreToolUse (Bash/PowerShell): devolve "ask" para comandos destrutivos ou externos,
# para que o usuário confirme mesmo quando um agent ignora as instruções do prompt.
# Não bloqueia nada sozinho: só obriga a confirmação. Sem dependências (sem jq).

input=$(cat)
command=$(printf '%s' "$input" | tr '\r\n' '  ')

S='[[:space:]]+'
patterns=(
  "git${S}push"
  "git${S}reset${S}--hard"
  "git${S}clean"
  "git${S}checkout${S}--"
  "git${S}restore"
  "git${S}rebase"
  "git${S}branch${S}-(D|-delete)"
  "git${S}stash${S}(drop|clear)"
  "git${S}(commit|merge|tag)([[:space:]]|\")"
  "(^|[^[:alnum:]_-])rm${S}-[[:alpha:]]*[rRf]"
  "Remove-Item"
  "kubectl${S}(apply|create|delete|replace|patch|edit|scale|rollout|drain|cordon|exec|set)"
  "helm${S}(install|upgrade|uninstall|delete|rollback)"
  "terraform${S}(apply|destroy|import|state|taint|untaint)"
  "argocd${S}app${S}(sync|delete|rollback|set|create)"
  "aws${S}s3${S}(cp|mv|rm|sync|rb|mb)"
  "aws${S}[[:alnum:]-]+${S}(create|delete|put|update|terminate|run|start|stop|modify|attach|detach|remove|send|publish|invoke|reboot|restore|tag|untag)"
  "docker${S}(push|login|system${S}prune|volume${S}(rm|prune))"
  "docker${S}compose${S}down${S}[^\"]*(-v|--volumes)"
  "(mvnw?|mvnw\\.cmd|gradlew?|gradlew\\.bat)${S}[^\"|;&]*(deploy|publish)"
  "flyway[:[:space:]]+[^\"|;&]*(clean|migrate|repair|baseline|undo)"
  "gh${S}(pr${S}(create|merge|close|comment|review)|release|repo${S}(delete|create)|secret|variable|workflow${S}run|api)"
  "npm${S}publish"
  "(psql|mysql|mongosh|redis-cli)${S}"
)

for pattern in "${patterns[@]}"; do
  if printf '%s' "$command" | grep -Eq -- "$pattern"; then
    printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"squads guardrail: comando destrutivo ou externo — confirme antes de executar."}}\n'
    exit 0
  fi
done

exit 0
