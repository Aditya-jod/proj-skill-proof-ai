import contextlib
import io
import time
from typing import Any, Dict, List

from .session_state import ProblemSpec


class CodeEvaluator:
    def __init__(self) -> None:
        pass

    def evaluate(self, code: str, problem: ProblemSpec) -> Dict[str, Any]:
        if not problem:
            return {"status": "error", "message": "No active problem", "passed": 0, "failed": 0, "details": []}

        namespace: Dict[str, Any] = {}
        stdout_capture = io.StringIO()
        start = time.perf_counter()
        try:
            with contextlib.redirect_stdout(stdout_capture):
                exec(code, namespace)
        except Exception as exc:
            duration = time.perf_counter() - start
            return {
                "status": "error",
                "message": f"Execution failed: {exc}",
                "stdout": stdout_capture.getvalue(),
                "passed": 0,
                "failed": len(problem.tests),
                "total_tests": len(problem.tests),
                "execution_time": duration,
                "details": [],
            }

        candidate = namespace.get(problem.entrypoint)
        if not callable(candidate):
            duration = time.perf_counter() - start
            return {
                "status": "error",
                "message": f"Function '{problem.entrypoint}' not defined",
                "stdout": stdout_capture.getvalue(),
                "passed": 0,
                "failed": len(problem.tests),
                "total_tests": len(problem.tests),
                "execution_time": duration,
                "details": [],
            }

        details: List[Dict[str, Any]] = []
        passed = 0
        for test in problem.tests:
            args = test.get("args", [])
            kwargs = test.get("kwargs", {})
            expected = test.get("expected")
            try:
                output = candidate(*args, **kwargs)
                ok = output == expected
                if ok:
                    passed += 1
                details.append({
                    "args": args,
                    "kwargs": kwargs,
                    "expected": expected,
                    "output": output,
                    "passed": ok,
                })
            except Exception as exc:
                details.append({
                    "args": args,
                    "kwargs": kwargs,
                    "expected": expected,
                    "error": str(exc),
                    "passed": False,
                })

        duration = time.perf_counter() - start
        total = len(problem.tests)
        failed = total - passed
        status = "passed" if failed == 0 else "partial" if passed > 0 else "failed"
        return {
            "status": status,
            "message": "All tests passed" if status == "passed" else "Tests failing",
            "stdout": stdout_capture.getvalue(),
            "passed": passed,
            "failed": failed,
            "total_tests": total,
            "execution_time": duration,
            "details": details,
        }
