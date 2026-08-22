"""
UMAY Reasoning & Planning Engine — Görev Anlama, Planlama ve Zincirli Çalıştırma.

Bu modül UMAY'ı "cevap veren AI"dan "görevi anlayan → planlayan →
çalıştıran → doğrulayan → raporlayan AI Agent"a dönüştürür.

%100 ÜCRETSIZ ve YEREL. Ollama LLM kullanır.

Mimari:
    Kullanıcı Görevi
        ↓
    ReasoningEngine (LLM ile görev anlama)
        ↓
    TaskDecomposer (görevi parçalara bölme)
        ↓
    ToolRouter (hangi tool gerektiğine karar verme)
        ↓
    ExecutionEngine (tool zincirlerini çalıştırma)
        ↓
    SelfVerifier (sonuç doğrulama)
        ↓
    RetryManager (hata durumunda tekrar deneme)
        ↓
    Rapor
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from core.engine import chat, resolve_model
from core.agent_tools import DISPATCH, TOOLS, ACTIVE_WORKSPACE
from core.utils.action_logger import eylem_baslat, eylem_tamamla, eylem_hata

# ─── Sabitler ────────────────────────────────────────────────────────────────

MAX_RETRIES = 3
MAX_STEPS = 20
MAX_PLAN_LENGTH = 15
TIMEOUT_PER_STEP = 120

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


# ─── Veri Modelleri ─────────────────────────────────────────────────────────

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskStatus(str, Enum):
    CREATED = "created"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class TaskStep:
    """Tek bir görev adımı."""
    id: str
    description: str
    tool_name: str
    arguments: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    retry_count: int = 0
    started_at: str | None = None
    completed_at: str | None = None


@dataclass
class TaskPlan:
    """Görev planı — birden fazla adımdan oluşur."""
    id: str
    goal: str
    steps: list[TaskStep]
    status: TaskStatus = TaskStatus.CREATED
    context: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str | None = None
    summary: str = ""


# ─── Tool Haritası ──────────────────────────────────────────────────────────

# Her tool'un hangi kategoride olduğunu tanımla
TOOL_CATEGORIES = {
    # Dosya/Belge okuma
    "read_file": {"category": "document_read", "keywords": ["oku", "dosya", "okuma", "read"]},
    "read_document": {"category": "document_read", "keywords": ["oku", "belge", "pdf", "word", "excel", "csv", "read"]},
    "list_directory": {"category": "file_system", "keywords": ["listele", "göz at", "listele", "klasör"]},
    "scan_directory": {"category": "document_read", "keywords": ["tara", "tarama", "tüm dosyalar", "scan"]},
    "search_files": {"category": "search", "keywords": ["ara", "bul", "search", "find"]},
    "search_in_documents": {"category": "search", "keywords": ["belgelerde ara", "içeride ara", "document search"]},

    # Görsel
    "analyze_image": {"category": "vision", "keywords": ["görsel", "resim", "analiz", "image", "fotoğraf"]},
    "image_to_text": {"category": "vision", "keywords": ["görselden metin", "ocr", "metin çıkar"]},
    "describe_image": {"category": "vision", "keywords": ["açıkla", "tanımla", "describe"]},
    "image_qa": {"category": "vision", "keywords": ["görsel soru", "resimde ne var"]},

    # Kod/Yazılım
    "write_file": {"category": "code_write", "keywords": ["yaz", "oluştur", "kaydet", "write"]},
    "run_command": {"category": "terminal", "keywords": ["çalıştır", "komut", "run", "execute", "cmd"]},
    "run_test_suite": {"category": "testing", "keywords": ["test", "pytest", "test çalıştır"]},
    "git_diff_summary": {"category": "git", "keywords": ["git", "diff", "değişiklik"]},

    # Web
    "web_search": {"category": "web_research", "keywords": ["araştır", "internette ara", "web", "search"]},
    "browser_open": {"category": "browser", "keywords": ["aç", "git", "open", "navigate"]},
    "browser_read": {"category": "browser", "keywords": ["sayfa oku", "okuma"]},
    "browser_click": {"category": "browser", "keywords": ["tıkla", "click"]},
    "browser_type": {"category": "browser", "keywords": ["yaz", "doldur", "type"]},
    "browser_screenshot": {"category": "browser", "keywords": ["ekran görüntüsü", "screenshot"]},

    # Hafıza
    "document_to_memory": {"category": "memory", "keywords": ["hafızaya kaydet", "memory", "remember"]},
    "image_to_memory": {"category": "memory", "keywords": ["görseli hafızaya", "görsel kaydet"]},

    # Proje analizi
    "inspect_project": {"category": "analysis", "keywords": ["proje analizi", "incele", "inspect"]},
    "rollback_backup": {"category": "recovery", "keywords": ["geri al", "rollback", "yedek"]},
}

# Kategori → tool eşleştirmesi
CATEGORY_TOOLS = {}
for tool_name, info in TOOL_CATEGORIES.items():
    cat = info["category"]
    if cat not in CATEGORY_TOOLS:
        CATEGORY_TOOLS[cat] = []
    CATEGORY_TOOLS[cat].append(tool_name)


# ─── Reasoning Engine ───────────────────────────────────────────────────────

REASONING_SYSTEM = """Sen UMAY'ın planlama motorusun. Kullanıcının görevini analiz et ve Somut bir plan oluştur.

KURALLAR:
1. Görevi net bir şekilde anla.
2. Gerekli araçları (tool'ları) belirle.
3. Adımları sıraya koy.
4. Her adım için tool adını ve argümanlarını yaz.
5. Kullanılabilecek tool'lar: {available_tools}
6. Her adım tek bir tool çağrısı olmalı.
7. Adımlar mantıksal sıralanmış olmalı.
8. Birden fazla tool'un birlikte çalışabileceği durumları belirt.
9. Gereksiz adım ekleme.
10. Mümkün olduğunca az adım ile görevi tamamla.

ÇIKTI FORMATI (SADECE JSON):
{{
    "understanding": "Görevin kısa özeti",
    "steps": [
        {{
            "description": "Adım açıklaması",
            "tool": "tool_adı",
            "args": {{"parametre": "değer"}}
        }}
    ],
    "reasoning": "Neden bu adımları seçtin?"
}}

ÖNEMLİ: Sadece JSON döndür. Başka hiçbir metin yazma."""


class ReasoningEngine:
    """LLM tabanlı akıl yürütme motoru."""

    def __init__(self, model: str | None = None):
        self.model = model or resolve_model("reasoning") or resolve_model("chat")

    def _build_available_tools_text(self) -> str:
        """Kullanılabilir tool listesini metin olarak oluştur."""
        lines = []
        for tool in TOOLS:
            name = tool["function"]["name"]
            desc = tool["function"]["description"]
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def understand_task(self, user_request: str) -> dict[str, Any]:
        """
        Kullanıcı görevini anla ve plan oluştur.

        Returns:
            dict: {understanding, steps, reasoning}
        """
        tools_text = self._build_available_tools_text()

        system = REASONING_SYSTEM.format(available_tools=tools_text)

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Görev: {user_request}\n\nBu görev için plan oluştur."},
        ]

        try:
            response = chat(
                messages,
                model=self.model,
                ajan="planner",
                task="reasoning",
            )

            if isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
            else:
                content = str(response)

            # JSON çıkar
            plan = self._extract_json(content)
            if plan:
                return plan

            # JSON çıkarılamazsa hata
            return {
                "understanding": user_request,
                "steps": [],
                "reasoning": "LLM geçerli JSON üretemedi",
                "raw_response": content[:500],
                "parse_error": True,
            }
        except Exception as e:
            return {
                "understanding": user_request,
                "steps": [],
                "reasoning": f"Hata: {e}",
                "parse_error": True,
            }

    def _extract_json(self, text: str) -> dict | None:
        """Metin içinden JSON çıkar."""
        # Direkt JSON dene
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # ```json bloklarından çıkar
        import re
        patterns = [
            r"```json\s*(\{.*?\})\s*```",
            r"```\s*(\{.*?\})\s*```",
            r"(\{[\s\S]*\"steps\"[\s\S]*\})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        return None

    def evaluate_step_result(
        self,
        original_goal: str,
        step_description: str,
        step_result: dict[str, Any],
        step_number: int,
        total_steps: int,
    ) -> dict[str, Any]:
        """
        Bir adımın sonucunu değerlendir.

        Returns:
            dict: {success, assessment, suggestion, should_continue}
        """
        eval_messages = [
            {"role": "system", "content": (
                "Sen UMAY'ın değerlendirici motorusun. "
                "Bir aracın (tool) çalışma sonucunu değerlendir.\n"
                "Sadece kısa ve net cevap ver.\n\n"
                "ÇIKTI FORMATI (JSON):\n"
                '{"success": true/false, "assessment": "değerlendirme", '
                '"suggestion": "öneri", "should_continue": true/false}'
            )},
            {"role": "user", "content": (
                f"Orijinal görev: {original_goal}\n"
                f"Bu {step_number}/{total_steps}. adım: {step_description}\n"
                f"Sonuç: {json.dumps(step_result, ensure_ascii=False)[:2000]}\n\n"
                f"Bu sonuç başarısız mı? Devam etmeli mi?"
            )},
        ]

        try:
            response = chat(
                eval_messages,
                model=self.model,
                ajan="planner_eval",
                task="reasoning",
            )

            content = str(response) if not isinstance(response, dict) else response.get("message", {}).get("content", "")

            # JSON çıkar
            import re
            match = re.search(r"\{[^{}]*\"success\"[^{}]*\}", content, re.DOTALL)
            if match:
                return json.loads(match.group())

            # Varsayılan: devam et
            return {
                "success": not bool(step_result.get("error")),
                "assessment": content[:200],
                "suggestion": "",
                "should_continue": True,
            }
        except Exception:
            return {
                "success": not bool(step_result.get("error")),
                "assessment": "Değerlendirme yapılamadı",
                "suggestion": "",
                "should_continue": True,
            }

    def generate_summary(
        self,
        original_goal: str,
        results: list[dict[str, Any]],
    ) -> str:
        """Görev sonunda özet rapor oluştur."""
        eval_messages = [
            {"role": "system", "content": (
                "Sen UMAY'ın raporlama motorusun. "
                "Görev sonuçlarını özetle. Kısa ve net yaz. Türkçe yaz."
            )},
            {"role": "user", "content": (
                f"Görev: {original_goal}\n\n"
                f"Adım sonuçları:\n"
                f"{json.dumps(results, ensure_ascii=False)[:3000]}\n\n"
                f"Kullanıcıya kısa özet rapor oluştur."
            )},
        ]

        try:
            response = chat(
                eval_messages,
                model=self.model,
                ajan="planner_summary",
                task="reasoning",
            )

            if isinstance(response, dict):
                return response.get("message", {}).get("content", "Özet oluşturulamadı.")
            return str(response)
        except Exception:
            return "Özet oluşturulamadı."


# ─── Task Decomposer ────────────────────────────────────────────────────────

class TaskDecomposer:
    """Görevleri alt görevlere böler."""

    def __init__(self, reasoning: ReasoningEngine):
        self.reasoning = reasoning

    def decompose(self, user_request: str) -> TaskPlan:
        """
        Kullanıcı görevini analiz et ve TaskPlan oluştur.

        Args:
            user_request: Kullanıcı isteği

        Returns:
            TaskPlan: Detaylı görev planı
        """
        plan_id = f"plan-{time.strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        # LLM'den plan oluştur
        llm_plan = self.reasoning.understand_task(user_request)

        # Adımları parse et
        steps = []
        raw_steps = llm_plan.get("steps", [])

        for i, raw_step in enumerate(raw_steps):
            tool_name = raw_step.get("tool", "")

            # Tool geçerli mi kontrol et
            if tool_name not in DISPATCH:
                # Tool adını düzeltmeyi dene
                tool_name = self._fuzzy_match_tool(tool_name)

            if tool_name and tool_name in DISPATCH:
                step = TaskStep(
                    id=f"step-{i + 1}",
                    description=raw_step.get("description", f"Adım {i + 1}"),
                    tool_name=tool_name,
                    arguments=raw_step.get("args", {}),
                )
                steps.append(step)

        if not steps:
            # Plan oluşturulamadı — basit bir fallback planı oluştur
            steps = self._create_fallback_steps(user_request)

        task_plan = TaskPlan(
            id=plan_id,
            goal=user_request,
            steps=steps,
            context={
                "understanding": llm_plan.get("understanding", ""),
                "reasoning": llm_plan.get("reasoning", ""),
            },
        )

        return task_plan

    def _fuzzy_match_tool(self, tool_name: str) -> str | None:
        """Tool adını fuzzy olarak eşleştir."""
        tool_name_lower = tool_name.lower().strip()

        # Doğrudan eşleşme
        if tool_name_lower in DISPATCH:
            return tool_name_lower

        # Kategori bazlı eşleşme
        for t_name, info in TOOL_CATEGORIES.items():
            if tool_name_lower in info["keywords"]:
                return t_name

        # Kısmi eşleşme
        for t_name in DISPATCH:
            if tool_name_lower in t_name or t_name in tool_name_lower:
                return t_name

        return None

    def _create_fallback_steps(self, user_request: str) -> list[TaskStep]:
        """LLM plan oluşturamazsa basit fallback planı."""
        request_lower = user_request.lower()

        steps = []

        # Anahtar kelime bazlı basit planlama
        if any(k in request_lower for k in ["oku", "oku bak", "okuma", "incele"]):
            if any(k in request_lower for k in ["pdf", "word", "excel", "csv", "belge"]):
                steps.append(TaskStep(
                    id="step-1", description="Belgeyi oku",
                    tool_name="read_document",
                    arguments={"path": self._extract_path(user_request) or "."},
                ))
            else:
                steps.append(TaskStep(
                    id="step-1", description="Dosyayı oku",
                    tool_name="read_file",
                    arguments={"path": self._extract_path(user_request) or "README.md"},
                ))

        elif any(k in request_lower for k in ["ara", "bul", "search"]):
            steps.append(TaskStep(
                id="step-1", description="Dosyalarda ara",
                tool_name="search_files",
                arguments={"pattern": self._extract_search_term(user_request) or "TODO"},
            ))

        elif any(k in request_lower for k in ["listele", "göz at", "tara"]):
            steps.append(TaskStep(
                id="step-1", description="Klasörü listele",
                tool_name="list_directory",
                arguments={"path": self._extract_path(user_request) or ".", "recursive": True},
            ))

        elif any(k in request_lower for k in ["çalıştır", "test"]):
            steps.append(TaskStep(
                id="step-1", description="Testleri çalıştır",
                tool_name="run_test_suite",
                arguments={},
            ))

        else:
            # Genel: dosyaları listele
            steps.append(TaskStep(
                id="step-1", description="Projeyi keşfet",
                tool_name="inspect_project",
                arguments={},
            ))

        return steps

    def _extract_path(self, text: str) -> str | None:
        """Metin içinden dosya/klasör yolu çıkar."""
        import re
        # Windows path
        match = re.search(r'[A-Z]:\\[^\s"\']+', text)
        if match:
            return match.group()
        # Dosya adı uzantılı
        match = re.search(r'[\w/\\.-]+\.\w{1,5}', text)
        if match:
            return match.group()
        return None

    def _extract_search_term(self, text: str) -> str | None:
        """Metin içinden arama terimi çıkar."""
        import re
        # Tırnak işaretleri arasındaki terim
        match = re.search(r'["\'](.+?)["\']', text)
        if match:
            return match.group(1)
        # "ara" kelimesinden sonraki terim
        match = re.search(r'ara[\"\s]+(.+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None


# ─── Execution Engine ───────────────────────────────────────────────────────

class ExecutionEngine:
    """Görev planını çalıştırır."""

    def __init__(self, retry_manager: RetryManager | None = None):
        self.retry_manager = retry_manager or RetryManager()
        self.results: list[dict[str, Any]] = []

    def execute_plan(
        self,
        plan: TaskPlan,
        reasoning: ReasoningEngine,
    ) -> TaskPlan:
        """
        Planı sırayla çalıştır.

        Args:
            plan: Çalıştırılacak plan
            reasoning: Değerlendirme için reasoning engine

        Returns:
            TaskPlan: Güncellenmiş plan (sonuçlarla)
        """
        plan.status = TaskStatus.EXECUTING
        self.results = []

        for step in plan.steps:
            if step.status == StepStatus.SKIPPED:
                continue

            # Bağımlılıkları kontrol et
            if not self._check_dependencies(step, plan.steps):
                step.status = StepStatus.SKIPPED
                step.error = "Bağımlılıklar karşılanmadı"
                continue

            # Adımı çalıştır
            success = self._execute_step(step, plan)

            # Sonucu değerlendir
            if success:
                evaluation = reasoning.evaluate_step_result(
                    original_goal=plan.goal,
                    step_description=step.description,
                    step_result=step.result or {},
                    step_number=int(step.id.split("-")[1]),
                    total_steps=len(plan.steps),
                )

                if not evaluation.get("success", True) and not evaluation.get("should_continue", True):
                    step.status = StepStatus.FAILED
                    step.error = evaluation.get("assessment", "Değerlendirme başarısız")
                    continue

                self.results.append({
                    "step": step.description,
                    "result": step.result,
                    "evaluation": evaluation,
                })
            else:
                # Retry dene
                retry_result = self.retry_manager.retry_step(step, self._execute_single_tool)

                if retry_result:
                    step.status = StepStatus.COMPLETED
                    self.results.append({
                        "step": step.description,
                        "result": step.result,
                        "retry": True,
                    })
                else:
                    step.status = StepStatus.FAILED
                    # Kritik adım başarısızsa planı durdur
                    if self._is_critical_step(step, plan):
                        plan.status = TaskStatus.FAILED
                        plan.summary = f"Kritik adım başarısız: {step.description}"
                        return plan

        # Tüm adımlar tamamlandı
        completed = sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED)
        failed = sum(1 for s in plan.steps if s.status == StepStatus.FAILED)

        if failed == 0:
            plan.status = TaskStatus.COMPLETED
        elif completed > 0:
            plan.status = TaskStatus.PARTIAL
        else:
            plan.status = TaskStatus.FAILED

        # Özet oluştur
        plan.completed_at = datetime.now().isoformat()
        plan.summary = reasoning.generate_summary(plan.goal, self.results)

        return plan

    def _execute_step(self, step: TaskStep, plan: TaskPlan) -> bool:
        """Tek bir adımı çalıştır."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()

        try:
            result = self._execute_single_tool(step.tool_name, step.arguments)
            step.result = result
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now().isoformat()
            return not bool(result.get("error"))
        except Exception as e:
            step.error = str(e)
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now().isoformat()
            return False

    def _execute_single_tool(self, tool_name: str, arguments: dict) -> dict[str, Any]:
        """Tek bir tool'u çalıştır."""
        if tool_name not in DISPATCH:
            return {"error": f"Bilinmeyen tool: {tool_name}"}

        try:
            func = DISPATCH[tool_name]
            result = func(**arguments)

            if isinstance(result, dict):
                return result
            return {"result": str(result), "status": "OK"}
        except PermissionError as e:
            return {"error": f"İzin hatası: {e}", "permission_required": True}
        except Exception as e:
            return {"error": f"Çalıştırma hatası: {e}"}

    def _check_dependencies(self, step: TaskStep, all_steps: list[TaskStep]) -> bool:
        """Adımın bağımlılıklarını kontrol et."""
        if not step.depends_on:
            return True

        step_ids = {s.id: s for s in all_steps}
        for dep_id in step.depends_on:
            dep = step_ids.get(dep_id)
            if not dep or dep.status != StepStatus.COMPLETED:
                return False

        return True

    def _is_critical_step(self, step: TaskStep, plan: TaskPlan) -> bool:
        """Adımın kritik olup olmadığını belirle."""
        # İlk adım kritiktir
        if step.id == plan.steps[0].id:
            return True
        # Tool adı "write", "run_command" gibi écriture/modify olan adımlar kritik değildir
        non_critical_tools = {"write_file", "run_command", "browser_click", "browser_type"}
        return step.tool_name not in non_critical_tools


# ─── Retry Manager ──────────────────────────────────────────────────────────

class RetryManager:
    """Hata durumunda tekrar deneme yöneticisi."""

    def __init__(self, max_retries: int = MAX_RETRIES):
        self.max_retries = max_retries

    def retry_step(
        self,
        step: TaskStep,
        execute_func,
    ) -> bool:
        """
        Başarısız adımı tekrar dene.

        Returns:
            bool: Başarılı mı?
        """
        for attempt in range(self.max_retries):
            if step.retry_count >= self.max_retries:
                break

            step.retry_count += 1
            step.status = StepStatus.RUNNING

            # Hata analizi
            error_strategy = self._analyze_error(step.error or "")

            # Argümanları düzelt
            fixed_args = self._fix_arguments(step.arguments, error_strategy)

            try:
                result = execute_func(step.tool_name, fixed_args)
                step.result = result

                if not result.get("error"):
                    step.status = StepStatus.COMPLETED
                    return True

                step.error = result.get("error", "Tekrar başarısız")
            except Exception as e:
                step.error = str(e)

        step.status = StepStatus.FAILED
        return False

    def _analyze_error(self, error_msg: str) -> dict[str, Any]:
        """Hata mesajını analiz et ve strateji belirle."""
        error_lower = error_msg.lower()

        strategy = {
            "type": "unknown",
            "fix_args": {},
            "suggestion": "",
        }

        if "bulunamadı" in error_lower or "not found" in error_lower:
            strategy["type"] = "not_found"
            strategy["suggestion"] = "Dosya/klasör yolu yanlış olabilir"

        elif "izin" in error_lower or "permission" in error_lower:
            strategy["type"] = "permission"
            strategy["suggestion"] = "İzin hatası — kullanıcı onayı gerekebilir"

        elif "timeout" in error_lower or "zaman aşımı" in error_lower:
            strategy["type"] = "timeout"
            strategy["suggestion"] = "İşlem zaman aşımına uğradı"

        elif "bağlanamadı" in error_lower or "connection" in error_lower:
            strategy["type"] = "connection"
            strategy["suggestion"] = "Servis çalışmıyor olabilir"

        return strategy

    def _fix_arguments(self, args: dict, strategy: dict) -> dict:
        """Hata stratejisine göre argümanları düzelt."""
        fixed = dict(args)

        if strategy["type"] == "not_found":
            # "." ile dene
            if "path" in fixed and fixed["path"] != ".":
                fixed["path"] = "."

        return fixed


# ─── Self Verifier ──────────────────────────────────────────────────────────

class SelfVerifier:
    """Görev sonunda sonuçları doğrular."""

    def __init__(self, reasoning: ReasoningEngine):
        self.reasoning = reasoning

    def verify(self, plan: TaskPlan) -> dict[str, Any]:
        """
        Görev planının sonuçlarını doğrula.

        Returns:
            dict: Doğrulama sonuçları
        """
        verification = {
            "plan_id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            "checks": [],
            "overall": True,
        }

        for step in plan.steps:
            check = {
                "step": step.description,
                "tool": step.tool_name,
                "status": step.status.value,
            }

            # Hata kontrolü
            if step.status == StepStatus.FAILED:
                check["issue"] = step.error
                verification["overall"] = False

            # Sonuç kontrolü
            if step.result:
                if step.result.get("error"):
                    check["issue"] = step.result["error"]
                    verification["overall"] = False
                elif step.result.get("status") == "ERROR":
                    check["issue"] = "Tool hata durumu döndürdü"
                    verification["overall"] = False

            verification["checks"].append(check)

        # Tüm adımlar atlandıysa
        active_steps = [s for s in plan.steps if s.status != StepStatus.SKIPPED]
        if not active_steps:
            verification["overall"] = False
            verification["issue"] = "Hiçbir adım çalıştırılmadı"

        return verification


# ─── Ana Orchestration Fonksiyonu ───────────────────────────────────────────

def plan_and_execute(
    user_request: str,
    model: str | None = None,
    max_steps: int = MAX_STEPS,
) -> dict[str, Any]:
    """
    UMAY'ın ana görev planlama ve çalıştırma fonksiyonu.

    Bu fonksiyon şu zinciri çalıştırır:
    1. Kullanıcı görevini anla
    2. Görevi parçalara böl
    3. Tool'ları seç
    4. Planı çalıştır
    5. Sonuçları doğrula
    6. Özet rapor oluştur

    Args:
        user_request: Kullanıcı isteği
        model: Kullanılacak model (None ise otomatik seç)
        max_steps: Maksimum adım sayısı

    Returns:
        dict: {plan, results, verification, summary}
    """
    # Action logging
    aid = eylem_baslat(
        ajan="planner",
        niyet=user_request[:100],
        plan=f"Reasoning + Planning engine; max_steps={max_steps}",
        model=model or "auto",
    )

    try:
        # 1. Reasoning Engine
        reasoning = ReasoningEngine(model=model)

        # 2. Task Decomposer
        decomposer = TaskDecomposer(reasoning)
        plan = decomposer.decompose(user_request)

        # Adım sayısını sınırla
        if len(plan.steps) > max_steps:
            plan.steps = plan.steps[:max_steps]

        plan.status = TaskStatus.PLANNING

        # 3. Execution Engine
        executor = ExecutionEngine()
        plan = executor.execute_plan(plan, reasoning)

        # 4. Self Verification
        verifier = SelfVerifier(reasoning)
        verification = verifier.verify(plan)

        # 5. Sonuç
        result = {
            "plan_id": plan.id,
            "goal": plan.goal,
            "status": plan.status.value,
            "steps": [
                {
                    "id": s.id,
                    "description": s.description,
                    "tool": s.tool_name,
                    "status": s.status.value,
                    "result_preview": str(s.result)[:500] if s.result else None,
                    "error": s.error,
                }
                for s in plan.steps
            ],
            "verification": verification,
            "summary": plan.summary,
            "total_steps": len(plan.steps),
            "completed_steps": sum(1 for s in plan.steps if s.status == StepStatus.COMPLETED),
            "failed_steps": sum(1 for s in plan.steps if s.status == StepStatus.FAILED),
        }

        eylem_tamamla(
            aid,
            f"Plan {plan.status.value}: {result['completed_steps']}/{result['total_steps']} adım tamamlandı",
            plan.status in (TaskStatus.COMPLETED, TaskStatus.PARTIAL),
            0,
        )

        return result

    except Exception as e:
        eylem_hata(aid, str(e))
        return {
            "status": "error",
            "error": str(e),
            "goal": user_request,
        }


# ─── Hızlı Erişim Fonksiyonları ─────────────────────────────────────────────

def quick_plan(user_request: str) -> TaskPlan:
    """Sadece plan oluştur, çalıştırma."""
    reasoning = ReasoningEngine()
    decomposer = TaskDecomposer(reasoning)
    return decomposer.decompose(user_request)


def quick_execute(plan: TaskPlan) -> dict[str, Any]:
    """Mevcut planı çalıştır."""
    reasoning = ReasoningEngine()
    executor = ExecutionEngine()
    plan = executor.execute_plan(plan, reasoning)
    verifier = SelfVerifier(reasoning)
    verification = verifier.verify(plan)
    return {"plan": plan, "verification": verification}


def smart_route(user_request: str) -> dict[str, Any]:
    """
    Akıllı yönlendirme — basit görevler için direkt çalıştır,
    karmaşık görevler için plan oluştur.
    """
    request_lower = user_request.lower()

    # Tek tool ile yapılabilen basit görevler
    simple_commands = {
        "oku": ("read_file", {"path": "README.md"}),
        "listele": ("list_directory", {"path": ".", "recursive": True}),
        "tara": ("inspect_project", {}),
        "test": ("run_test_suite", {}),
        "git": ("git_diff_summary", {}),
    }

    for keyword, (tool, default_args) in simple_commands.items():
        if keyword in request_lower:
            if tool in DISPATCH:
                return {
                    "type": "simple",
                    "tool": tool,
                    "result": DISPATCH[tool](**default_args),
                }

    # Karmaşık görev — plan oluştur ve çalıştır
    return plan_and_execute(user_request)


# ─── Test Fonksiyonu ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== UMAY Reasoning & Planning Engine Test ===\n")

    # Test 1: Basit plan
    print("Test 1: Basit plan oluştur...")
    plan = quick_plan("Projedeki dosyaları listele ve README.md dosyasını oku")
    print(f"  Plan ID: {plan.id}")
    print(f"  Adım sayısı: {len(plan.steps)}")
    for step in plan.steps:
        print(f"  - {step.description} ({step.tool_name})")

    # Test 2: Akıllı yönlendirme
    print("\nTest 2: Akıllı yönlendirme...")
    result = smart_route("projeyi listele")
    print(f"  Tip: {result.get('type')}")
    if result.get("type") == "simple":
        print(f"  Tool: {result.get('tool')}")

    print("\nTest tamamlandı.")
