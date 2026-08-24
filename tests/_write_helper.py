
import base64, os
data = base64.b64decode(open(os.path.join("tests", "_b64.txt")).read().strip())
with open(os.path.join("tests", "test_step05_task_executor.py"), "wb") as f:
    f.write(data)
print("Written:", os.path.getsize(os.path.join("tests", "test_step05_task_executor.py")))
os.remove(os.path.join("tests", "_b64.txt"))
