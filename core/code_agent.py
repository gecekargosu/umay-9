"""
UMAY Code Agent — Çok Dilli Kod Okuma, Yazma, Analiz ve Test.

Bu modül UMAY'ın gerçek anlamda kodlama yapmasını sağlar.

Desteklenen diller:
- Python
- JavaScript / TypeScript
- HTML / CSS
- SQL
- JSON / YAML
- Shell / PowerShell
- React (JSX/TSX)

Özellikler:
- Kod okuma ve açıklama
- Kod yazma
- Hata tespit ve çözüm
- Test yazma ve çalıştırma
- Build ve lint
- Proje analizi
- Refactor önerileri

%100 ÜCRETSIZ ve YEREL.
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from core.engine import chat, resolve_model
from core.utils.action_logger import eylem_baslat, eylem_hata, eylem_tamamla

# ─── Sabitler ────────────────────────────────────────────────────────────────

MAX_CODE_CHARS = 30_000
DEFAULT_TIMEOUT = 30

# Desteklenen dosya uzantıları ve diller
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sh": "shell",
    ".bash": "shell",
    ".ps1": "powershell",
    ".bat": "batch",
    ".cmd": "batch",
    ".md": "markdown",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "config",
    ".xml": "xml",
    ".vue": "vue",
    ".svelte": "svelte",
}


# ─── Kod Temizleme ──────────────────────────────────────────────────────────

def clean_code(text: str) -> str:
    """LLM çıktısından saf kodu çıkar."""
    text = text.strip()
    if not text:
        return ""

    if "```" not in text:
        return text

    blocks = []
    lines = text.splitlines()
    inside = False
    for line in lines:
        if line.strip().startswith("```"):
            inside = not inside
            continue
        if inside:
            blocks.append(line)

    result = "\n".join(blocks).strip()
    if result:
        return result

    # Fallback
    return text.replace("```python", "").replace("```javascript", "").replace("```", "").strip()


def detect_language(file_path: str) -> str:
    """Dosya uzantısından dili tespit et."""
    ext = Path(file_path).suffix.lower()
    return LANGUAGE_MAP.get(ext, "unknown")


def truncate_code(code: str, max_chars: int = MAX_CODE_CHARS) -> str:
    """Kodu belirli bir karakter sınırıyla kısalt."""
    if len(code) <= max_chars:
        return code
    return code[:max_chars] + f"\n# [... Kısaltıldı: {len(code)} karakter ...]"


# ─── Kod Okuma ve Analiz ────────────────────────────────────────────────────

def read_code(file_path: str, start_line: int = 1, max_lines: int = 500) -> dict[str, Any]:
    """
    Kod dosyasını oku ve analiz et.

    Returns:
        dict: {content, language, line_count, analysis}
    """
    path = Path(file_path)

    if not path.exists():
        return {"error": f"Dosya bulunamadı: {file_path}", "status": "ERROR"}

    if not path.is_file():
        return {"error": f"Bu bir dosya değil: {file_path}", "status": "ERROR"}

    try:
        content = path.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total_lines = len(lines)

        # Dil tespiti
        language = detect_language(file_path)

        # Satır aralığı
        start = max(1, start_line)
        end = min(total_lines, start - 1 + max_lines)
        selected_lines = lines[start - 1:end]
        selected_content = "\n".join(f"{i + start}: {line}" for i, line in enumerate(selected_lines))

        # Basit analiz
        analysis = _analyze_code_structure(content, language)

        return {
            "path": str(path.name),
            "language": language,
            "total_lines": total_lines,
            "start_line": start,
            "end_line": end,
            "content": truncate_code(selected_content),
            "analysis": analysis,
            "status": "OK",
        }
    except Exception as e:
        return {"error": f"Kod okuma hatası: {e}", "status": "ERROR"}


def _analyze_code_structure(code: str, language: str) -> dict[str, Any]:
    """Kod yapısını analiz et."""
    analysis = {
        "language": language,
        "line_count": len(code.splitlines()),
        "char_count": len(code),
    }

    if language == "python":
        try:
            tree = ast.parse(code)
            classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            analysis["classes"] = classes
            analysis["functions"] = functions
            analysis["imports"] = imports
            analysis["class_count"] = len(classes)
            analysis["function_count"] = len(functions)
        except SyntaxError:
            analysis["syntax_error"] = True

    elif language in ("javascript", "typescript"):
        # Basit regex tabanlı analiz
        analysis["functions"] = re.findall(r"(?:function|const|let|var)\s+(\w+)", code)
        analysis["classes"] = re.findall(r"class\s+(\w+)", code)
        analysis["imports"] = re.findall(r"import\s+.*?from\s+['\"](.+?)['\"]", code)

    elif language == "html":
        analysis["tags"] = re.findall(r"<(\w+)", code)
        analysis["has_form"] = "<form" in code.lower()
        analysis["has_script"] = "<script" in code.lower()

    return analysis


# ─── Kod Yazma ───────────────────────────────────────────────────────────────

def generate_code(
    description: str,
    language: str = "python",
    model: str | None = None,
    context: str = "",
) -> dict[str, Any]:
    """
    LLM ile kod üret.

    Args:
        description: İstenen kodun açıklaması
        language: Programlama dili
        model: Kullanılacak model
        context: Ek bağlam

    Returns:
        dict: {code, language, model}
    """
    selected_model = model or resolve_model("coding") or resolve_model("chat")

    if not selected_model:
        return {"error": "Kullanılabilir coding modeli bulunamadı.", "status": "ERROR"}

    # system_prompt burada tanımlanmıyor, chat çağrısında kullanılıyor

    # Dil adını düzelt
    lang_display = language.upper() if language != "powershell" else "PowerShell"

    user_prompt = f"Şu işi yapan {lang_display} kodunu yaz:\n{description}"
    if context:
        user_prompt += f"\n\nBağlam:\n{context}"

    aid = eylem_baslat(
        ajan="code_agent",
        niyet=f"Kod yazma ({language}): {description[:60]}",
        plan=f"Model: {selected_model}",
        model=selected_model,
    )

    try:
        response = chat(
            [
                {"role": "system", "content": f"Sen UMAY'in Coding Agent'isin. {lang_display} dilinde çalışan kod yaz. Açıklama yazma; yalnızca saf kod döndür."},
                {"role": "user", "content": user_prompt},
            ],
            model=selected_model,
            ajan="code_agent",
            task="coding",
        )

        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
        else:
            content = str(response)

        code = clean_code(content)

        if not code:
            return {"error": "Model boş kod döndürdü.", "status": "ERROR"}

        eylem_tamamla(aid, f"Kod üretildi ({len(code)} karakter)", True)

        return {
            "code": code,
            "language": language,
            "model": selected_model,
            "char_count": len(code),
            "status": "OK",
        }
    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": f"Kod üretme hatası: {e}", "status": "ERROR"}


# ─── Kod Açıklama ────────────────────────────────────────────────────────────

def explain_code(
    code: str,
    language: str = "python",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Kodu açıkla.

    Args:
        code: Açıklanacak kod
        language: Programlama dili
        model: Kullanılacak model

    Returns:
        dict: {explanation, language}
    """
    selected_model = model or resolve_model("reasoning") or resolve_model("chat")

    if not selected_model:
        return {"error": "Kullanılabilir model bulunamadı.", "status": "ERROR"}

    aid = eylem_baslat(
        ajan="code_agent",
        niyet=f"Kod açıklama ({language})",
        plan=f"Model: {selected_model}",
        model=selected_model,
    )

    try:
        response = chat(
            [
                {"role": "system", "content": (
                    "Sen UMAY'in kod analiz uzmanısın. Verilen kodu detaylı şekilde açıkla.\n"
                    "Şunları belirt:\n"
                    "1. Kodun ne yaptığını kısa özetle\n"
                    "2. Ana fonksiyonları/sınıfları açıkla\n"
                    "3. Önemli mantıksal akışı tanımla\n"
                    "4. Varsa potansiyel sorunları belirt\n"
                    "Türkçe yaz."
                )},
                {"role": "user", "content": f"Dil: {language}\n\nKod:\n```\n{truncate_code(code, 15000)}\n```"},
            ],
            model=selected_model,
            ajan="code_agent",
            task="reasoning",
        )

        if isinstance(response, dict):
            explanation = response.get("message", {}).get("content", "")
        else:
            explanation = str(response)

        eylem_tamamla(aid, "Kod açıklama tamamlandı", True)

        return {
            "explanation": explanation,
            "language": language,
            "status": "OK",
        }
    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": f"Kod açıklama hatası: {e}", "status": "ERROR"}


# ─── Hata Tespit ve Düzeltme ────────────────────────────────────────────────

def find_bugs(
    code: str,
    language: str = "python",
    error_message: str = "",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Kodda hata tespit et.

    Args:
        code: Analiz edilecek kod
        language: Programlama dili
        error_message: Bilinen hata mesajı (varsa)
        model: Kullanılacak model

    Returns:
        dict: {bugs, suggestions, fixed_code}
    """
    selected_model = model or resolve_model("coding") or resolve_model("chat")

    if not selected_model:
        return {"error": "Kullanılabilir model bulunamadı.", "status": "ERROR"}

    aid = eylem_baslat(
        ajan="code_agent",
        niyet=f"Hata tespiti ({language})",
        plan=f"Model: {selected_model}",
        model=selected_model,
    )

    try:
        user_content = f"Dil: {language}\n\nKod:\n```\n{truncate_code(code, 15000)}\n```"
        if error_message:
            user_content += f"\n\nHata mesajı:\n{error_message}"

        response = chat(
            [
                {"role": "system", "content": (
                    "Sen UMAY'in debug uzmanısın. Verilen kodda hataları tespit et.\n"
                    "Şunları yap:\n"
                    "1. Hataları listele (konum ve açıklama ile)\n"
                    "2. Her hata için düzeltme önerisi ver\n"
                    "3. Düzeltilmiş kodu göster\n"
                    "Türkçe yaz. JSON formatında döndür:\n"
                    '{"bugs": [{"line": N, "description": "...", "severity": "high/medium/low"}], '
                    '"suggestions": ["..."], "fixed_code": "..."}'
                )},
                {"role": "user", "content": user_content},
            ],
            model=selected_model,
            ajan="code_agent",
            task="coding",
        )

        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
        else:
            content = str(response)

        # JSON çıkar
        result = _extract_json_from_response(content)

        eylem_tamamla(aid, "Hata tespiti tamamlandı", True)

        return {
            "bugs": result.get("bugs", []),
            "suggestions": result.get("suggestions", []),
            "fixed_code": result.get("fixed_code", ""),
            "language": language,
            "raw_response": content[:1000] if not result else None,
            "status": "OK",
        }
    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": f"Hata tespit hatası: {e}", "status": "ERROR"}


def _extract_json_from_response(text: str) -> dict | None:
    """LLM yanıtından JSON çıkar."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    patterns = [
        r"```json\s*(\{.*?\})\s*```",
        r"```\s*(\{.*?\})\s*```",
        r"(\{[\s\S]*\"bugs\"[\s\S]*\})",
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

    return None


# ─── Test Yazma ve Çalıştırma ────────────────────────────────────────────────

def write_test(
    code: str,
    language: str = "python",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Verilen kod için test yaz.

    Args:
        code: Test yazılacak kod
        language: Programlama dili
        model: Kullanılacak model

    Returns:
        dict: {test_code, language}
    """
    selected_model = model or resolve_model("coding") or resolve_model("chat")

    if not selected_model:
        return {"error": "Kullanılabilir model bulunamadı.", "status": "ERROR"}

    aid = eylem_baslat(
        ajan="code_agent",
        niyet=f"Test yazma ({language})",
        plan=f"Model: {selected_model}",
        model=selected_model,
    )

    try:
        response = chat(
            [
                {"role": "system", "content": (
                    "Sen UMAY'in test yazma uzmanısın. Verilen kod için kapsamlı test yaz.\n"
                    "Python için pytest kullan.\n"
                    "Test cases: normal, edge case, hata durumu.\n"
                    "Yalnızca test kodunu döndür, açıklama yazma."
                )},
                {"role": "user", "content": f"Dil: {language}\n\nKod:\n```\n{truncate_code(code, 15000)}\n```\n\nBu kod için test yaz."},
            ],
            model=selected_model,
            ajan="code_agent",
            task="coding",
        )

        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
        else:
            content = str(response)

        test_code = clean_code(content)

        eylem_tamamla(aid, f"Test yazıldı ({len(test_code)} karakter)", True)

        return {
            "test_code": test_code,
            "language": language,
            "status": "OK",
        }
    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": f"Test yazma hatası: {e}", "status": "ERROR"}


def run_tests(
    test_path: str = "tests/",
    command: str = "python -m pytest",
    timeout: int = 120,
) -> dict[str, Any]:
    """
    Testleri çalıştır.

    Args:
        test_path: Test dosyası/klasörü yolu
        command: Çalıştırılacak komut
        timeout: Zaman aşımı

    Returns:
        dict: {output, returncode, passed, failed}
    """
    aid = eylem_baslat(
        ajan="code_agent",
        niyet=f"Test çalıştırma: {test_path}",
        plan=f"Komut: {command}",
        model="",
    )

    try:
        full_command = f"{command} {test_path} -v --tb=short"
        result = subprocess.run(
            full_command,
            capture_output=True,
            text=True,
            shell=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )

        output = result.stdout or ""
        stderr = result.stderr or ""

        # Sonuçları parse et
        passed = len(re.findall(r"PASSED", output))
        failed = len(re.findall(r"FAILED", output))
        errors = len(re.findall(r"ERROR", output))

        success = result.returncode == 0

        eylem_tamamla(
            aid,
            f"Testler: {passed} passed, {failed} failed, {errors} errors",
            success,
        )

        return {
            "command": full_command,
            "returncode": result.returncode,
            "stdout": output[-MAX_CODE_CHARS:],
            "stderr": stderr[-5000:],
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "status": "PASS" if success else "FAIL",
        }
    except subprocess.TimeoutExpired:
        eylem_hata(aid, f"Test zaman aşımı ({timeout}s)")
        return {
            "error": f"Test zaman aşımı: {timeout} saniye",
            "status": "TIMEOUT",
        }
    except Exception as e:
        eylem_hata(aid, str(e))
        return {"error": f"Test çalıştırma hatası: {e}", "status": "ERROR"}


# ─── Proje Analizi ──────────────────────────────────────────────────────────

def analyze_project(
    project_path: str = ".",
) -> dict[str, Any]:
    """
    Proje yapısını analiz et.

    Args:
        project_path: Proje klasörü

    Returns:
        dict: Proje analiz sonuçları
    """
    path = Path(project_path)

    if not path.exists():
        return {"error": f"Proje bulunamadı: {project_path}", "status": "ERROR"}

    # Dosya türlerini say
    file_counts = {}
    total_files = 0
    total_size = 0

    skip_dirs = {".git", "__pycache__", ".venv", "node_modules", "dist", "build",
                ".next", ".cache", ".umay_backups", "chroma", ".freebuff"}

    for item in path.rglob("*"):
        if not item.is_file():
            continue
        if any(part in skip_dirs for part in item.parts):
            continue

        ext = item.suffix.lower()
        lang = LANGUAGE_MAP.get(ext, "other")
        file_counts[lang] = file_counts.get(lang, 0) + 1
        total_files += 1
        total_size += item.stat().st_size

    # Proje türünü tespit et
    project_type = _detect_project_type(path)

    return {
        "path": str(path),
        "project_type": project_type,
        "total_files": total_files,
        "total_size": total_size,
        "file_counts": file_counts,
        "languages": sorted(file_counts.keys()),
        "status": "OK",
    }


def _detect_project_type(path: Path) -> str:
    """Proje türünü tespit et."""
    files = {f.name.lower() for f in path.iterdir() if f.is_file()}

    if "pyproject.toml" in files or "setup.py" in files or "requirements.txt" in files:
        return "python"
    if "package.json" in files:
        return "node"
    if "cargo.toml" in files:
        return "rust"
    if "go.mod" in files:
        return "go"
    if "pom.xml" in files or "build.gradle" in files:
        return "java"
    if "composer.json" in files:
        return "php"
    if "gemfile" in files:
        return "ruby"
    if "dockerfile" in files or "docker-compose.yml" in files:
        return "docker"
    return "unknown"


# ─── Ana Fonksiyonlar ───────────────────────────────────────────────────────

def code_assist(
    request: str,
    code: str = "",
    language: str = "python",
    model: str | None = None,
) -> dict[str, Any]:
    """
    Kod asistanı — çok yönlü yardim.

    Args:
        request: Kullanıcı isteği
        code: İlgili kod (varsa)
        language: Programlama dili
        model: Kullanılacak model

    Returns:
        dict: Asistan sonucu
    """
    request_lower = request.lower()

    # İsteğe göre yönlendir
    if any(k in request_lower for k in ["yaz", "oluştur", "create", "write"]):
        return generate_code(request, language=language, model=model)

    elif any(k in request_lower for k in ["açıkla", "explain", "anlat"]):
        if code:
            return explain_code(code, language=language, model=model)
        else:
            return {"error": "Açıklanacak kod gerekli", "status": "ERROR"}

    elif any(k in request_lower for k in ["hata", "bug", "debug", "düzelt"]):
        if code:
            return find_bugs(code, language=language, model=model)
        else:
            return {"error": "Analiz edilecek kod gerekli", "status": "ERROR"}

    elif any(k in request_lower for k in ["test", "pytest"]):
        if code:
            return write_test(code, language=language, model=model)
        else:
            return run_tests(request)

    elif any(k in request_lower for k in ["proje", "project", "analiz"]):
        return analyze_project(request)

    else:
        # Genel: kod üret
        return generate_code(request, language=language, model=model)


# ─── Test Fonksiyonu ────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=== UMAY Code Agent Test ===\n")

    # Test 1: Kod okuma
    test_file = Path(__file__).parent.parent / "README.md"
    if test_file.exists():
        result = read_code(str(test_file))
        print(f"Test 1 - Kod okuma: {result.get('status')}")
        print(f"  Dil: {result.get('language')}")

    # Test 2: Dil tespiti
    print("\nTest 2 - Dil tespiti:")
    print(f"  .py → {detect_language('test.py')}")
    print(f"  .js → {detect_language('test.js')}")
    print(f"  .tsx → {detect_language('test.tsx')}")

    # Test 3: Proje analizi
    result = analyze_project(str(Path(__file__).parent.parent))
    print("\nTest 3 - Proje analizi:")
    print(f"  Tip: {result.get('project_type')}")
    print(f"  Dosya sayısı: {result.get('total_files')}")
    print(f"  Diller: {result.get('languages')}")
