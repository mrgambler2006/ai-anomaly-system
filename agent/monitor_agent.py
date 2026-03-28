import argparse
import ctypes
import json
from pathlib import Path
import subprocess
import socket
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
import sys

import psutil

try:
    import pyttsx3
except ModuleNotFoundError:
    pyttsx3 = None


MB_ICONWARNING = 0x30
MB_OK = 0x0


class BackgroundMonitorAgent:
    def __init__(self, server_url, interval_seconds=1, popup_cooldown_seconds=1):
        self.server_url = server_url.rstrip("/")
        self.interval_seconds = interval_seconds
        self.popup_cooldown_seconds = popup_cooldown_seconds
        self.repo_root = Path(__file__).resolve().parent.parent
        self.hostname = socket.gethostname()
        self.last_popup_at = None
        self.last_voice_at = None
        self.popup_active = False
        self.voice_active = False
        self.previous_result = None
        self.previous_mode = None
        self.previous_process_ids = set(psutil.pids())
        self.backend_process = None
        self.backend_launch_attempted = False
        psutil.cpu_percent(interval=None)

    def collect_metrics(self):
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage("/").percent
        return {
            "cpu": cpu,
            "ram": ram,
            "disk": disk,
            "hostname": self.hostname,
            "source": "background-agent",
        }

    def get_process_ids(self):
        try:
            return set(psutil.pids())
        except Exception:
            return set()

    def send_metrics(self, payload):
        request = urllib.request.Request(
            f"{self.server_url}/agent/telemetry",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def can_auto_start_backend(self):
        parsed = urllib.parse.urlparse(self.server_url)
        return parsed.scheme in {"http", "https"} and parsed.hostname in {"127.0.0.1", "localhost"}

    def ensure_backend_running(self):
        if not self.can_auto_start_backend():
            return False

        if self.backend_process is not None and self.backend_process.poll() is None:
            return True

        if self.backend_launch_attempted:
            return False

        parsed = urllib.parse.urlparse(self.server_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        try:
            creationflags = 0
            if hasattr(subprocess, "DETACHED_PROCESS"):
                creationflags |= subprocess.DETACHED_PROCESS
            if hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
                creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP

            self.backend_process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.main:app",
                    "--host",
                    host,
                    "--port",
                    str(port),
                ],
                cwd=self.repo_root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=creationflags,
            )
            self.backend_launch_attempted = True
            print(f"Local backend was not running. Started it with {sys.executable} on {host}:{port}.")
            return True
        except Exception as exc:
            self.backend_launch_attempted = True
            print(f"Could not auto-start backend: {exc}")
            print(
                "Start it manually with: "
                f"\"{sys.executable}\" -m uvicorn backend.main:app --host {host} --port {port}"
            )
            return False

    def should_show_popup(self):
        if self.last_popup_at is None:
            return True
        return datetime.now() - self.last_popup_at >= timedelta(seconds=self.popup_cooldown_seconds)

    def show_popup(self, result, title=None, message=None):
        if not self.should_show_popup() or self.popup_active:
            return

        alert_title = title
        if not alert_title:
            if result["critical"]:
                alert_title = "Critical System Alert"
            elif result.get("mode") == "high":
                alert_title = "High Load Activity Warning"
            else:
                alert_title = "System Overload Warning"

        popup_message = message or (
            f"System Alert on {result.get('hostname', self.hostname)}\n\n"
            f"Prediction: {result['prediction']}\n"
            f"Reason: {result['reason']}\n"
            f"CPU: {result['data']['cpu']}%\n"
            f"RAM: {result['data']['ram']}%\n"
            f"Disk: {result['data']['disk']}%"
        )

        def _popup_worker():
            self.popup_active = True
            try:
                ctypes.windll.user32.MessageBoxW(0, popup_message, alert_title, MB_OK | MB_ICONWARNING)
            finally:
                self.popup_active = False

        self.last_popup_at = datetime.now()
        threading.Thread(target=_popup_worker, daemon=True).start()

    def high_load_alert_message(self, result):
        return (
            f"High CPU load detected on {result.get('hostname', self.hostname)}.\n\n"
            "Too many active processes are using the CPU.\n"
            f"CPU: {result['data']['cpu']}%\n"
            f"RAM: {result['data']['ram']}%\n"
            f"Disk: {result['data']['disk']}%\n\n"
            "Close heavy background apps to reduce load."
        )

    def show_cpu_overload_popup(self, result):
        self.show_popup(
            result,
            title="High CPU Load Warning",
            message=self.high_load_alert_message(result),
        )

    def should_speak_voice(self):
        if self.last_voice_at is None:
            return True
        return datetime.now() - self.last_voice_at >= timedelta(seconds=self.popup_cooldown_seconds)

    def speak_cpu_overload_voice(self, message="High CPU load detected. Close background apps to reduce load."):
        if self.voice_active or not self.should_speak_voice():
            return

        def _voice_worker():
            self.voice_active = True
            try:
                spoken = False

                if pyttsx3 is not None:
                    try:
                        engine = pyttsx3.init()
                        engine.say(message)
                        engine.runAndWait()
                        spoken = True
                    except Exception:
                        spoken = False

                if not spoken:
                    escaped_message = message.replace("'", "''")
                    ps_command = (
                        "Add-Type -AssemblyName System.Speech; "
                        "$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                        f"$speaker.Speak('{escaped_message}')"
                    )
                    subprocess.run(
                        ["powershell", "-Command", ps_command],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
            except Exception as exc:
                print(f"CPU overload voice failed: {exc}")
            finally:
                self.voice_active = False

        self.last_voice_at = datetime.now()
        threading.Thread(target=_voice_worker, daemon=True).start()

    def should_alert_for_high_mode_activity(self, result):
        current_process_ids = self.get_process_ids()
        new_process_count = len(current_process_ids - self.previous_process_ids)
        self.previous_process_ids = current_process_ids

        if result.get("mode") != "high":
            return False

        current_data = result.get("data", {})
        current_cpu = current_data.get("cpu", 0)
        if current_cpu < 50:
            return False

        if new_process_count > 0:
            return True

        if self.previous_result is None:
            return current_cpu >= 50

        previous_data = self.previous_result.get("data", {})
        cpu_jump = current_data.get("cpu", 0) - previous_data.get("cpu", 0)
        ram_jump = current_data.get("ram", 0) - previous_data.get("ram", 0)
        disk_jump = current_data.get("disk", 0) - previous_data.get("disk", 0)

        return (
            cpu_jump >= 1
            or ram_jump >= 1
            or disk_jump >= 1
            or current_data.get("cpu", 0) >= 50
        )

    def should_alert_for_real_cpu_overload(self, result):
        current_cpu = result.get("data", {}).get("cpu", 0)
        previous_cpu = 0
        if self.previous_result is not None:
            previous_cpu = self.previous_result.get("data", {}).get("cpu", 0)
        return current_cpu >= 50 and previous_cpu < 50

    def switched_to_high_mode(self, result):
        current_mode = result.get("mode")
        return current_mode == "high" and self.previous_mode != "high"

    def should_alert_immediately_for_high_mode(self, result):
        if result.get("mode") != "high":
            return False

        current_cpu = result.get("data", {}).get("cpu", 0)
        return self.switched_to_high_mode(result) and current_cpu >= 50

    def trigger_immediate_high_mode_alert(self, result):
        self.show_cpu_overload_popup(result)
        self.speak_cpu_overload_voice()

    def run_forever(self):
        print(f"Background agent started for {self.hostname}")
        while True:
            try:
                payload = self.collect_metrics()
                result = self.send_metrics(payload)
                print(
                    f"[{result['timestamp']}] CPU={result['data']['cpu']} RAM={result['data']['ram']} "
                    f"DISK={result['data']['disk']} anomaly={result['anomaly']} critical={result['critical']}"
                )
                if self.should_alert_immediately_for_high_mode(result):
                    self.trigger_immediate_high_mode_alert(result)
                elif self.should_alert_for_real_cpu_overload(result):
                    self.show_cpu_overload_popup(result)
                    self.speak_cpu_overload_voice()
                if self.should_alert_for_high_mode_activity(result):
                    self.show_popup(result)
                self.previous_mode = result.get("mode")
                self.previous_result = result
            except urllib.error.URLError as exc:
                if self.ensure_backend_running():
                    time.sleep(2)
                    try:
                        result = self.send_metrics(payload)
                        print(
                            f"[{result['timestamp']}] CPU={result['data']['cpu']} RAM={result['data']['ram']} "
                            f"DISK={result['data']['disk']} anomaly={result['anomaly']} critical={result['critical']}"
                        )
                        if self.should_alert_immediately_for_high_mode(result):
                            self.trigger_immediate_high_mode_alert(result)
                        elif self.should_alert_for_real_cpu_overload(result):
                            self.show_cpu_overload_popup(result)
                            self.speak_cpu_overload_voice()
                        if self.should_alert_for_high_mode_activity(result):
                            self.show_popup(result)
                        self.previous_mode = result.get("mode")
                        self.previous_result = result
                        time.sleep(self.interval_seconds)
                        continue
                    except urllib.error.URLError:
                        pass
                print(f"Could not reach backend: {exc}")
            except Exception as exc:
                print(f"Agent error: {exc}")

            time.sleep(self.interval_seconds)


def main():
    parser = argparse.ArgumentParser(description="AI anomaly system background monitor")
    parser.add_argument("--server-url", default="http://127.0.0.1:8000", help="Backend URL")
    parser.add_argument("--interval", type=int, default=1, help="Telemetry send interval in seconds")
    parser.add_argument("--popup-cooldown", type=int, default=1, help="Popup cooldown in seconds")
    args = parser.parse_args()

    agent = BackgroundMonitorAgent(
        server_url=args.server_url,
        interval_seconds=max(1, args.interval),
        popup_cooldown_seconds=max(1, args.popup_cooldown),
    )
    agent.run_forever()


if __name__ == "__main__":
    main()
