import os
import subprocess
import sys

SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "scripts", "check_env.py")


def test_check_env_script_file_exists():
    assert os.path.isfile(SCRIPT_PATH), f"脚本不存在: {SCRIPT_PATH}"


def test_check_env_script_does_not_print_secret_values():
    result = subprocess.run(
        [sys.executable, SCRIPT_PATH],
        capture_output=True, text=True, timeout=10,
    )
    output = result.stdout + result.stderr
    # 不应包含真实 API key 片段
    assert "sk-" not in output, f"输出包含疑似 key: {output}"
    assert "Bearer" not in output, f"输出包含授权信息: {output}"
