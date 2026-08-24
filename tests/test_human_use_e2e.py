"""E2E Human-Use Test — Intent → Model → Tool → Execution"""
import sys, os
sys.stdout.reconfigure(encoding="utf-8")
os.environ["UMAY_APPROVED"] = "true"

PASSED = 0
FAILED = 0

def check(label, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  PASS: {label} {detail}")
    else:
        FAILED += 1
        print(f"  FAIL: {label} {detail}")

print("=" * 60)
print("UMAY E2E HUMAN-USE TEST")
print("=" * 60)

# ─── INTENT ROUTING ───
print("\n--- INTENT ROUTING ---")
from core.intent_router import classify_intent

routing_tests = [
    ("Merhaba nasilsin", "chat"),
    ("engine.py dosyasinin ilk 10 satirini goster", "file"),
    ("requirements.txt icinde ne var", "file"),
    ("core klasorunu listele", "file"),
    ("Python class yaz", "code"),
    ("def add(a,b) fonksiyonunu acikla", "code"),
    ("engine.pydeki hatayi bul", "code"),
    ("10 + 20 kac", "calculator"),
    ("25 * 4", "calculator"),
    ("100 / 5 kac", "calculator"),
    ("dosyaya bunu yaz", "file"),
    ("klasordeki dosyalari listele", "file"),
    ("hava durumu nasil", "web"),
    ("10 satir Python kodu yaz", "code"),
    ("Python ile hesap makinesi yap", "code"),
]
for msg, expected in routing_tests:
    result = classify_intent(msg)
    val = result.value if hasattr(result, "value") else str(result)
    check(f"Intent: '{msg}'", val == expected, f"-> {val} (expected {expected})")

# ─── MODEL ROUTING ───
print("\n--- MODEL ROUTING ---")
from core.engine import resolve_model

model_tests = [
    ("chat", "phi4-mini"),
    ("code", "gpt-oss"),
    ("coding", "gpt-oss"),
    ("reasoning", "gpt-oss"),
    ("analysis", "gpt-oss"),
    ("file", "phi4-mini"),
    ("calculator", "phi4-mini"),
    ("web", "phi4-mini"),
]
for task, expected_prefix in model_tests:
    model = resolve_model(task)
    name = model.get("model", str(model)) if isinstance(model, dict) else str(model)
    ok = expected_prefix.lower() in name.lower()
    check(f"Model: {task}", ok, f"-> {name}")

# ─── TOOL EXECUTION ───
print("\n--- TOOL EXECUTION ---")
from core.agent_tools import read_file, list_directory, run_command, evaluate_expression, search_files, write_file

# File read
r = read_file(path="core/engine.py", start_line=1, max_lines=3)
check("read_file: engine.py", "import" in r.get("content", "") or '"""' in r.get("content", ""))

# Directory list
r = list_directory(path="core")
entries = r.get("entries", [])
check("list_directory: core/", len(entries) > 5, f"({len(entries)} entries)")

# Run command
r = run_command(command="echo hello_umay")
check("run_command: echo", "hello_umay" in r.get("stdout", ""))

# Calculator
r = evaluate_expression(expression="10 + 20")
check("evaluate_expression: 10+20", "30" in str(r.get("result", r.get("answer", ""))))

# Search glob
r = search_files(pattern="*.py", path="core")
matches = r.get("matches", [])
check("search_files: *.py glob", len(matches) > 5, f"({len(matches)} matches)")

# Search content
r = search_files(pattern="resolve_model", path="core/engine.py")
matches = r.get("matches", [])
check("search_files: content regex", len(matches) > 0, f"({len(matches)} matches)")

# Write + read (inside workspace)
import pathlib
workspace = pathlib.Path(os.environ.get("UMAY_WORKSPACE", "."))
test_file = workspace / ".umay_e2e_test.txt"
write_file(path=str(test_file), content="UMAY E2E TEST BASARILI")
r = read_file(path=str(test_file), start_line=1, max_lines=1)
check("write_file + read_file roundtrip", "UMAY E2E TEST BASARILI" in r.get("content", ""))
test_file.unlink(missing_ok=True)  # cleanup

# ─── SUMMARY ───
print("\n" + "=" * 60)
total = PASSED + FAILED
print(f"RESULT: {PASSED}/{total} PASS, {FAILED} FAIL")
print("=" * 60)
if FAILED > 0:
    raise AssertionError(f'{FAILED} tests failed')
