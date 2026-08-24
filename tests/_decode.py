
import base64, os
b64 = open(os.path.join("tests","_test.b64")).read().strip()
content = base64.b64decode(b64).decode("utf-8")
with open(os.path.join("tests","test_step05_task_executor.py"), "w", encoding="utf-8") as f:
    f.write(content)
print("Written:", os.path.getsize(os.path.join("tests","test_step05_task_executor.py")))
os.remove(os.path.join("tests","_test.b64"))
