"""Launch the real curses game in a pseudo-terminal and walk the menus."""

import os
import select
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

try:
    import fcntl
    import pty
    import struct
    import termios
except ImportError:  # pragma: no cover - non-POSIX
    pty = None

# curses enables keypad mode, so arrow keys use application sequences
KEYS = {"ENTER": b"\r", "ESC": b"\x1b", "DOWN": b"\x1bOB", "RIGHT": b"\x1bOC"}


@unittest.skipIf(pty is None, "needs a POSIX pty")
class CursesWalkthroughTest(unittest.TestCase):
    def _drain(self, fd, seconds):
        out = b""
        end = time.time() + seconds
        while time.time() < end:
            ready, _, _ = select.select([fd], [], [], 0.05)
            if ready:
                try:
                    chunk = os.read(fd, 65536)
                except OSError:
                    break
                if not chunk:
                    break
                out += chunk
        return out

    def test_walk_every_screen_and_exit(self):
        home = tempfile.mkdtemp()
        pid, fd = pty.fork()
        if pid == 0:  # child
            os.environ.update(HOME=home, TERM="xterm", LANG="C.UTF-8", LC_ALL="C.UTF-8")
            os.execvp(sys.executable, [sys.executable, os.path.join(ROOT, "aquafarm.py")])
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 24, 80, 0, 0))
        script = [
            "ENTER",                   # accept fish profile
            "1", "1", "q",             # aquarium: feed fish
            "2", "1", "q",             # bonsai: water
            "3", "1", "3", "q",        # farm: water, plant
            "4", "ENTER", "1", "q",    # barn: profile, feed
            "5", "3", "ENTER", "1", "5", "9", "q", "x", "q",  # crows game, quit
            "6", "q", "7", "3", "q", "q", "8", "q", "9", "1", "q",
        ]
        output = self._drain(fd, 1.5)
        for key in script:
            os.write(fd, KEYS.get(key, key.encode()))
            output += self._drain(fd, 0.25)
        os.write(fd, b"q")
        output += self._drain(fd, 1.5)
        deadline = time.time() + 5
        status = None
        while time.time() < deadline:
            done, status = os.waitpid(pid, os.WNOHANG)
            if done:
                break
            time.sleep(0.1)
        else:
            os.kill(pid, 9)
            self.fail("game did not exit")
        os.close(fd)
        self.assertEqual(os.waitstatus_to_exitcode(status), 0, output[-2000:])
        self.assertNotIn(b"Traceback", output)
        save_dir = os.path.join(home, ".aquafarm")
        self.assertTrue(any(n.endswith("_homestead.dat") for n in os.listdir(save_dir)))

        sys.path.insert(0, ROOT)
        import json

        full = [n for n in os.listdir(save_dir) if n.endswith("_homestead_full.json")][0]
        with open(os.path.join(save_dir, full)) as handle:
            data = json.load(handle)
        stats = data["progress"]["stats"]
        for event in ("fish_fed", "bonsai_watered", "crops_watered", "crop_planted",
                      "animal_fed", "minigame_played"):
            self.assertIn(event, stats, f"{event} missing: {stats}")


if __name__ == "__main__":
    unittest.main()
