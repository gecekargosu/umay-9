"""UMAY autonomous workspace agent with a real Ollama tool loop."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from core.engine import chat, resolve_model
from core.agent_tools import TOOLS, DISPATCH, PROJECT_ROOT, set_workspace, get_workspace
from core.utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata
from core.task_state import start_task, checkpoint, finish_task, load_task, waiting_for_approval, resume_task
from core.approval_manager import (
    ApprovalManager, get_approval_manager, needs_approval,
    request_approval as _request_approval, approve as _approve,
    get_pending_approval, get_approval_by_id, TaskStatus,
)

# identity.py'den merkezi UMAY kimlik sistemi import ediliyor.
# Artık agent.py'de hardcoded prompt yok — tum identity identity.py'den gelir.
from core.identity import UMAY_SYSTEM, CHAT_IDENTITY

AUDIT_DIR = PROJECT_ROOT / "logs"
AUDIT_FILE = AUDIT_DIR / "DEVELOPMENT_LOG.md"
REPORT_FILE = PROJECT_ROOT / "UMAY_ENGINEERING_AUDIT.md"


def _log_markdown(title: str, body: str):
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as f:
        f.write(f"\n## {datetime.now():%Y-%m-%d %H:%M:%S} — {title}\n{body}\n")


def _extract_windows_path(text: str) -> str | None:
    """Extract an actual Windows directory from a natural-language request.

    Example:
        'C:\\CREWINTEL projesini baştan sona incele'
    must yield:
        'C:\\CREWINTEL'

    Never consume the rest of the Turkish sentence as part of the path.
    """
    # Drive-rooted path: consume Windows path characters only. A whitespace
    # starts the natural-language part, so we stop there. This intentionally
    # handles the common project-root form used by UMAY.
    m = re.search(r'(?i)([a-z]:\\[^\s"\'<>|?*]+)', text)
    if not m:
        # UNC path fallback. Stop at whitespace for the same reason.
        m = re.search(r'(\\\\[^\\s"\'<>|?*]+)', text)
    if not m:
        return None

    path = m.group(1).rstrip(".,;:!?)]}")
    # Remove a trailing slash only when it is not the root itself.
    if len(path) > 3:
        path = path.rstrip("\\/")
    return path or None

MAX_TOOL_RESULT_CHARS = 18_000


def _normalize_tool_call(call: dict, index: int = 0) -> dict:
    fn = dict(call.get("function") or {})
    name = fn.get("name")
    raw_args = fn.get("arguments", {})
    if isinstance(raw_args, str):
        try:
            args = json.loads(raw_args) if raw_args.strip() else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"Tool arguments JSON bozuk ({name}): {exc}") from exc
    elif isinstance(raw_args, dict):
        args = raw_args
    else:
        args = {}
    if not isinstance(args, dict):
        raise ValueError(f"Tool arguments object değil ({name})")
    return {
        "id": call.get("id") or f"umay-tool-{index}-{name or 'unknown'}",
        "type": call.get("type", "function"),
        "function": {"name": name, "arguments": args},
    }


def _parse_tool_calls(msg: dict) -> list[dict]:
    calls = msg.get("tool_calls") or []
    if calls:
        return [_normalize_tool_call(c, i) for i, c in enumerate(calls)]
    content = (msg.get("content") or "").strip()
    if not content:
        return []
    candidates=[content]
    candidates.extend(re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", content, flags=re.S))
    for candidate in candidates:
        try: obj=json.loads(candidate)
        except Exception: continue
        if isinstance(obj,dict) and obj.get("name") in DISPATCH:
            return [_normalize_tool_call({"id":f"compat-{obj['name']}","type":"function","function":{"name":obj["name"],"arguments":obj.get("arguments") or {}}})]
    return []


def _assistant_tool_message(tool_calls: list[dict]) -> dict:
    """Serialize normalized tool calls back into the Ollama chat protocol.

    Keep the model-provided tool-call id when available. Some Ollama-compatible
    clients accept messages without it, but preserving the id makes the
    assistant -> tool correlation deterministic and avoids losing protocol
    metadata between turns.
    """
    serialized = []
    for call in tool_calls:
        fn = call.get("function") or {}
        serialized.append({
            "id": call.get("id"),
            "type": call.get("type", "function"),
            "function": {
                "name": fn.get("name"),
                "arguments": fn.get("arguments") or {},
            },
        })
    return {"role": "assistant", "content": "", "tool_calls": serialized}


def _normalize_tool_paths(args: dict) -> dict:
    r"""Normalize Windows host paths to Docker container paths in tool arguments.
    
    When LLM produces paths like C:\Users\...\Desktop, convert to /host/Desktop.
    Only affects path-like arguments in filesystem tools.
    """
    import re as _re
    PATH_KEYS = {'path', 'directory', 'folder', 'file_path', 'target', 'backup_relative', 'target_relative'}
    # Windows path to Docker container path mapping
    _win_to_docker = {
        '/desktop': '/host/Desktop',
        '/documents': '/host/Documents',
        '/downloads': '/host/Downloads',
        '/masaustu': '/host/Desktop',
        '/belgeler': '/host/Documents',
        '/indirilenler': '/host/Downloads',
    }
    normalized = dict(args)
    for key in PATH_KEYS:
        if key in normalized and isinstance(normalized[key], str):
            val = normalized[key]
            # Already a Docker path — skip
            if val.startswith('/host/') or val.startswith('/app/'):
                continue
            # Windows path: C:\Users\<user>\Desktop\... → /host/Desktop/...
            m = _re.match(r'(?i)[a-z]:\\users\\[^\\]+\\(.+)', val)
            if m:
                remainder = m.group(1).replace('\\', '/')
                # Map common Windows folder names
                remainder_lower = remainder.lower().split('/')[0]
                docker_base = _win_to_docker.get('/' + remainder_lower, None)
                if docker_base:
                    rest = '/'.join(remainder.split('/')[1:]) if '/' in remainder else ''
                    normalized[key] = f"{docker_base}/{rest}".rstrip('/') if rest else docker_base
                continue
            # C:\Users\<user>\Desktop (no trailing path)
            m2 = _re.match(r'(?i)[a-z]:\\users\\[^\\]+\\(desktop|documents|downloads|masaustu|belgeler|indirilenler)$', val)
            if m2:
                folder = m2.group(1).lower()
                docker_base = _win_to_docker.get('/' + folder)
                if docker_base:
                    normalized[key] = docker_base
            # Bare folder name: "Desktop" → /host/Desktop
            _bare_folders = {
                'desktop': '/host/Desktop', 'documents': '/host/Documents',
                'downloads': '/host/Downloads', 'masaustu': '/host/Desktop',
                'masaüstü': '/host/Desktop', 'belgeler': '/host/Documents',
                'indirilenler': '/host/Downloads',
            }
            val_lower = val.strip().lower()
            if val_lower in _bare_folders and os.path.exists(_bare_folders[val_lower]):
                normalized[key] = _bare_folders[val_lower]
    return normalized


def _execute_tool(call: dict) -> tuple[dict, dict]:
    call=_normalize_tool_call(call)
    fn=call.get("function") or {}; name=fn.get("name"); args=fn.get("arguments") or {}
    if name not in DISPATCH: return call,{"error":f"Bilinmeyen tool: {name}"}
    # Normalize Windows paths to Docker paths for filesystem tools
    FILESYSTEM_TOOLS = {'list_directory', 'read_file', 'search_files', 'read_document', 'scan_directory', 'search_in_documents', 'open_file', 'open_folder'}
    if name in FILESYSTEM_TOOLS:
        args = _normalize_tool_paths(args)
    try:
        print(f"[UMAY AI][EL] {name}({json.dumps(args, ensure_ascii=False)})")
        result=DISPATCH[name](**args)
        preview=json.dumps(result,ensure_ascii=False)
        print(f"[UMAY AI][EL SONUCU] {preview[:800]}{'...' if len(preview)>800 else ''}")
        return call,result
    except Exception as exc:
        print(f"[UMAY AI][EL HATASI] {name}: {exc}")
        return call,{"error":str(exc),"tool":name}


def _bounded_tool_result(result: dict) -> str:
    content=json.dumps(result,ensure_ascii=False)
    if len(content)<=MAX_TOOL_RESULT_CHARS: return content
    # Preserve metadata and indicate truncation; model can request narrower data.
    if isinstance(result,dict):
        slim={"truncated":True,"original_chars":len(content)}
        for k in ("workspace","path","pattern","count","returncode","command","tool"):
            if k in result: slim[k]=result[k]
        if "entries" in result and isinstance(result["entries"],list):
            slim["shown_entries"]=result["entries"][:50]
        elif "matches" in result and isinstance(result["matches"],list):
            slim["shown_matches"]=result["matches"][:50]
        slim["message"]="Tool sonucu bağlam sınırı nedeniyle kısaltıldı; daha dar bir tool çağrısı yap."
        content=json.dumps(slim,ensure_ascii=False)
    return content[:MAX_TOOL_RESULT_CHARS]


def _tool_messages(tool_calls: list[dict]) -> list[dict]:
    messages=[]
    for call in tool_calls:
        call,result=_execute_tool(call)
        fn=call.get("function") or {}
        msg={"role":"tool","content":_bounded_tool_result(result),"tool_call_id":call["id"],"tool_name":fn.get("name")}
        messages.append(msg)
    return messages

def run_agent(
    request: str,
    max_steps: int = 40,
    task_id: str | None = None,
    resume: bool = False,
    context: dict | None = None,
) -> str:
    routed_task = "coding"
    routed_model = None
    if context and context.get("channel") in ("telegram", "telegram_user") and not context.get("resume"):
        from core.router import model_sec
        routed_model, routed_task = model_sec(request)
    model = routed_model or resolve_model(routed_task) or resolve_model("coding") or resolve_model("chat")
    if not model:
        return "Kurulu kullanılabilir Ollama modeli yok."

    target = _extract_windows_path(request)
    if target:
        try:
            active = set_workspace(target)
        except Exception as exc:
            return f"Agent hedef workspace'i açamadı: {exc}"
    else:
        active = get_workspace()

    previous = None
    approval = None
    if resume and task_id:
        previous = load_task(task_id)
        if not previous:
            return f"Resume başarısız: task bulunamadı: {task_id}"
        if previous.get("workspace") != str(active):
            return "Resume başarısız: task workspace'i aktif workspace ile eşleşmiyor."
        if previous.get("model"):
            model = previous["model"]
        # Approval durumunu kontrol et, approved kaydı da restart sonrası bulunabilsin.
        approval_id = previous.get("approval_id")
        approval = get_approval_by_id(approval_id) if approval_id else get_pending_approval(task_id)
        if approval:
            if approval.status == TaskStatus.APPROVED.value:
                # Onay verildi — tool'u çalıştır ve devam et
                resume_task(task_id, approval.pending_step or previous.get("step", 0), str(active))
            elif approval.status == TaskStatus.REJECTED.value:
                finish_task(task_id, previous.get("step", 0), "CANCELLED", "Kullanıcı onayı reddetti")
                return f"Görev iptal edildi: Kullanıcı onayı reddetti (task: {task_id})"

    task_id = start_task(request, str(active), model, task_id=task_id) if not resume else task_id
    aid = eylem_baslat(
        "umay_agent", request[:100],
        f"Workspace agent; max_steps={max_steps}; hedef={active}; task_id={task_id}", model
    )
    _log_markdown(
        "Agent görevi başladı",
        f"- UMAY kökü: `{PROJECT_ROOT}`\n- Aktif workspace: `{active}`\n- Model: `{model}`\n- İstek: {request}",
    )

    # ─── FAZ 2: Intent Router Integration ──────────────────────────────────
    is_chat = context and context.get("channel") in ("telegram", "telegram_user")
    
    # Intent sınıflandırması
    Intent = None  # type: ignore
    try:
        from core.intent_router import classify_intent, get_available_tools as intent_tools, Intent
        intent = classify_intent(request)
    except (ImportError, Exception):
        intent = "chat" if is_chat else None
    
    # Intent'e göre system prompt seçimi
    if is_chat:
        _chat_intents = ("chat", "knowledge") if Intent is None else (Intent.CHAT, Intent.KNOWLEDGE)
        if intent in _chat_intents:
            system_prompt = CHAT_IDENTITY
        else:
            # ACTION/TIME/FILE/DOCUMENT/VISION/WEB/CODE/TERMINAL/COMPLEX
            system_prompt = UMAY_SYSTEM + f"\n\nAktif workspace: {active}"
    else:
        system_prompt = UMAY_SYSTEM + f"\n\nAktif workspace: {active}"
    
    # Intent'e göre tool seçimi
    intent_tools_list = None
    if is_chat:
        try:
            intent_tools_list = intent_tools(intent)  # None = tool kullanma
        except Exception:
            intent_tools_list = None
    
    # Intent'e göre model/ task seçimi (sadece telegram/chat kanalında)
    if is_chat and not routed_model:
        from core.router import model_sec
        routed_model_new, routed_task_new = model_sec(request)
        if intent_tools_list is not None:
            # Tool kullanılacaksa tool-capable model seç
            routed_model = routed_model_new
            routed_task = routed_task_new
        else:
            # Basit sohbet → chat model
            routed_task = "chat"
            routed_model = resolve_model("chat")

    # Conversation history (Telegram/session bazlı)
    history_messages = []
    if is_chat and context and context.get("session_id"):
        try:
            from core import conversation_store as _conv
            session_id = context["session_id"]
            raw_history = _conv.get_history(session_id, max_pairs=10)
            for h in raw_history:
                role = h.get("role", "user")
                content = h.get("content", "")
                if content and role in ("user", "assistant"):
                    history_messages.append({"role": role, "content": content})
        except Exception as exc:
            from core.utils.logger import log
            log(f"[AGENT] Conversation history okunamadi: {exc}")


    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history_messages)
    messages.append({"role": "user", "content": request})

    # Kaydet: kullanıcının mesajını conversation store'a
    if is_chat and context and context.get("session_id"):
        try:
            from core import conversation_store as _conv
            _conv.add_message(context["session_id"], "user", request)
        except Exception:
            pass

    if resume and previous and isinstance(previous.get("messages"), list) and previous.get("messages"):
        messages = previous["messages"]
    if (
        resume
        and approval
        and approval.status == TaskStatus.APPROVED.value
        and approval.pending_tool_call
    ):
        approved_call = _normalize_tool_call(approval.pending_tool_call)
        messages.append(_assistant_tool_message([approved_call]))
        messages.extend(_tool_messages([approved_call]))

    try:
        for step in range(max_steps):
            # FAZ 2: Intent-based tool selection
            if is_chat:
                use_tools = intent_tools_list  # None for CHAT/KNOWLEDGE, tool list for ACTION etc.
            else:
                use_tools = TOOLS
            result = chat(
                messages, model=model, ajan="umay_agent",
                task=routed_task, tools=use_tools
            )
            msg = result.get("message", {}) if isinstance(result, dict) else {}
            tool_calls = _parse_tool_calls(msg)

            if tool_calls:
                # Approval kontrolü: her tool call için onay gerekiyor mu?
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    tc_name = fn.get("name", "")
                    tc_args = fn.get("arguments") or {}
                    if needs_approval(tc_name):
                        # Onay talebi oluştur
                        action, target = ApprovalManager.describe_action(tc_name, tc_args)
                        risk = ApprovalManager.get_tool_risk(tc_name)
                        apr = _request_approval(
                            task_id=task_id,
                            tool_name=tc_name,
                            action=action,
                            target=target,
                            reason=f"{tc_name} tool'u {risk} risk seviyesinde",
                            risk=risk,
                            tool_args=tc_args,
                            pending_tool_call=tc,
                            pending_messages=messages,
                            pending_step=step + 1,
                            owner_user_id=(context or {}).get("telegram_user_id"),
                            owner_chat_id=(context or {}).get("telegram_chat_id"),
                        )
                        # Task state'i WAITING_FOR_APPROVAL olarak kaydet
                        waiting_for_approval(
                            task_id=task_id,
                            step=step + 1,
                            workspace=str(active),
                            approval_id=apr.id,
                            tool_name=tc_name,
                            action=action,
                            target=target,
                            risk=risk,
                            messages=messages,
                        )
                        if context and context.get("channel") in ("telegram", "telegram_user"):
                            from core.communication_manager import get_communication_manager
                            get_communication_manager().send_approval_required(
                                channel=context["channel"],
                                task_id=task_id,
                                approval_id=apr.id,
                                tool_name=tc_name,
                                action=action,
                                target=target,
                                risk=risk,
                                telegram_chat_id=context.get("telegram_chat_id"),
                            )
                        _log_markdown(
                            "Onay bekleniyor",
                            f"- Task ID: `{task_id}`\n- Approval ID: `{apr.id}`\n- Tool: `{tc_name}`\n- Risk: {risk}\n- Action: {action}",
                        )
                        return f"[WAITING_FOR_APPROVAL] Onay gerekiyor: {apr.id} — {action}"

                messages.append(_assistant_tool_message(tool_calls))

                messages.extend(_tool_messages(tool_calls))
                tool_names = [(c.get("function") or {}).get("name", "?") for c in tool_calls]
                checkpoint(task_id, step + 1, str(active), "WAITING_MODEL", tool_names, messages)
                _log_markdown(
                    "Tool adımı",
                    f"- Task ID: `{task_id}`\n- Step: {step + 1}\n- Workspace: `{active}`\n- Tool sayısı: {len(tool_calls)}\n- Tool'lar: {', '.join(tool_names)}",
                )
                continue

            answer = msg.get("content", "") if msg else str(result)
            answer = (answer or "").strip()
            if not answer:
                raise RuntimeError("Agent modelden boş son cevap aldı.")

            eylem_tamamla(aid, answer[:500], True, 0)
            finish_task(task_id, step + 1, "COMPLETED", answer)
            # Proactive Telegram notification
            if is_chat and context and context.get("channel") in ("telegram", "telegram_user"):
                try:
                    from core.telegram_user_adapter import get_telegram_user_adapter
                    tg = get_telegram_user_adapter()
                    if tg.is_active():
                        tg.notify_task_complete(task_id, answer, context.get("telegram_chat_id"))
                except Exception:
                    pass
            _log_markdown(
                "Agent görevi tamamlandı",
                f"- Task ID: `{task_id}`\n- Adım: {step + 1}\n- Workspace: `{active}`\n- Sonuç:\n{answer[:4000]}",
            )
            # Telegram cevabını conversation store'a kaydet
            if is_chat and context and context.get("session_id"):
                try:
                    from core import conversation_store as _conv
                    _conv.add_message(context["session_id"], "assistant", answer)
                except Exception:
                    pass
            return answer

        raise RuntimeError(f"Agent adım limiti doldu ({max_steps}).")
    except Exception as exc:
        eylem_hata(aid, str(exc))
        # Proactive error notification
        if context and context.get("channel") in ("telegram", "telegram_user"):
            try:
                from core.telegram_user_adapter import get_telegram_user_adapter
                tg = get_telegram_user_adapter()
                if tg.is_active():
                    tg.notify_error(str(exc), request[:200], context.get("telegram_chat_id"))
            except Exception:
                pass
        _log_markdown("Agent hatası", f"- Workspace: `{active}`\n- Hata: `{exc}`")
        return f"Agent hatası: {exc}"


def approve_task(task_id: str, responded_by: str = "user", message: str = "") -> str:
    """Dış adapter'lar (Telegram, Web, Voice) tarafından çağrılır.

    Task'ın bekleyen onayını onaylar.
    Task resume edilebilir hale gelir.
    """
    apr = get_pending_approval(task_id)
    if not apr:
        return f"Onay bulunamadı: {task_id}"
    result = _approve(apr.id, responded_by=responded_by, message=message)
    if not result:
        return f"Onay verilemedi: {task_id}"
    return f"Onay verildi: {task_id} — {apr.action}"


def audit_and_fix_umay() -> str:
    """Perform deterministic first-pass audit and save findings."""
    report = []
    for f in PROJECT_ROOT.rglob("*.py"):
        if any(part in {"__pycache__", "chroma"} for part in f.parts):
            continue
        try:
            compile(f.read_text(encoding="utf-8", errors="ignore"), str(f), "exec")
        except SyntaxError as e:
            report.append(f"CRITICAL {f.relative_to(PROJECT_ROOT)}:{e.lineno} syntax error: {e.msg}")
    report.append("HIGH Tool loop: engine + agent now support native and JSON-compatible tool calls.")
    report.append("HIGH Dynamic target workspace: C:\\CREWINTEL gibi harici proje yolları artık aktif workspace olarak seçilebilir.")
    report.append("HIGH Tool result -> model feedback loop implemented with repeated steps.")
    report.append("MEDIUM Compatibility parser added for local models that emit tool-call JSON in message content.")
    REPORT_FILE.write_text(
        "# UMAY Engineering Audit\n\n" + "\n".join(f"- {x}" for x in report) + "\n",
        encoding="utf-8",
    )
    _log_markdown("Yeni agent loop denetimi", "\n".join(f"- {x}" for x in report))
    return "Yeni agent loop denetimi tamamlandı."
