import os
import io
import sys
import unittest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List

import listener.listen as listen


class TestDeviceSelection(unittest.TestCase):
    def setUp(self):
        self.mock_devices = [
            {"name": "MacBook Pro Microphone", "max_input_channels": 1, "max_output_channels": 0},
            {"name": "MacBook Pro Speakers", "max_input_channels": 0, "max_output_channels": 2},
            {"name": "BlackHole 2ch", "max_input_channels": 2, "max_output_channels": 2},
            {"name": "Understudy Audio Aggregate", "max_input_channels": 2, "max_output_channels": 2},
            {"name": "External USB Mic", "max_input_channels": 1, "max_output_channels": 0},
        ]

    @patch("sounddevice.query_devices")
    @patch("sounddevice.default")
    def test_list_input_devices(self, mock_default, mock_query):
        mock_query.return_value = self.mock_devices
        mock_default.device = (0, 1)

        captured = io.StringIO()
        with patch("sys.stdout", captured):
            listen.list_input_devices()

        out = captured.getvalue()
        self.assertIn("Available Audio Input Devices:", out)
        self.assertIn("[0] MacBook Pro Microphone (1 in) (default)", out)
        self.assertIn("[2] BlackHole 2ch (2 in)", out)
        self.assertNotIn("MacBook Pro Speakers", out)  # Should filter out output-only device

    @patch("sounddevice.query_devices")
    @patch("sounddevice.default")
    def test_explicit_env_substring_match(self, mock_default, mock_query):
        mock_query.return_value = self.mock_devices
        mock_default.device = (0, 1)

        with patch.dict(os.environ, {"AUDIO_DEVICE": "External USB"}):
            idx, name = listen.resolve_input_device()
            self.assertEqual(idx, 4)
            self.assertEqual(name, "External USB Mic")

    @patch("sounddevice.query_devices")
    @patch("sounddevice.default")
    def test_explicit_device_arg_override(self, mock_default, mock_query):
        mock_query.return_value = self.mock_devices
        mock_default.device = (0, 1)

        with patch.dict(os.environ, {"AUDIO_DEVICE": "External USB"}):
            idx, name = listen.resolve_input_device(device_query="BlackHole")
            self.assertEqual(idx, 2)
            self.assertEqual(name, "BlackHole 2ch")

    @patch("sounddevice.query_devices")
    @patch("sounddevice.default")
    def test_explicit_env_index_match(self, mock_default, mock_query):
        mock_query.return_value = self.mock_devices
        mock_default.device = (0, 1)

        with patch.dict(os.environ, {"AUDIO_DEVICE": "2"}):
            idx, name = listen.resolve_input_device()
            self.assertEqual(idx, 2)
            self.assertEqual(name, "BlackHole 2ch")

    @patch("sounddevice.query_devices")
    @patch("sounddevice.default")
    def test_auto_prefer_system_audio(self, mock_default, mock_query):
        mock_query.return_value = self.mock_devices
        mock_default.device = (0, 1)

        # When AUDIO_DEVICE is unset, it should prefer BlackHole or Understudy or Aggregate
        with patch.dict(os.environ, {}, clear=True):
            idx, name = listen.resolve_input_device()
            self.assertIn(idx, (2, 3))
            self.assertIn(name, ("BlackHole 2ch", "Understudy Audio Aggregate"))

    @patch("sounddevice.query_devices")
    @patch("sounddevice.default")
    def test_fallback_to_default_mic(self, mock_default, mock_query):
        devices = [
            {"name": "MacBook Pro Microphone", "max_input_channels": 1, "max_output_channels": 0},
            {"name": "MacBook Pro Speakers", "max_input_channels": 0, "max_output_channels": 2},
        ]
        mock_query.return_value = devices
        mock_default.device = (0, 1)

        with patch.dict(os.environ, {}, clear=True):
            idx, name = listen.resolve_input_device()
            self.assertEqual(idx, 0)
            self.assertEqual(name, "MacBook Pro Microphone")

    @patch("sounddevice.query_devices")
    def test_no_input_devices_fallback(self, mock_query):
        mock_query.return_value = [
            {"name": "Speaker Only", "max_input_channels": 0, "max_output_channels": 2},
        ]
        idx, name = listen.resolve_input_device()
        self.assertIsNone(idx)
        self.assertEqual(name, "Default")


class TestMeetingAppDetection(unittest.TestCase):
    @patch("psutil.process_iter")
    def test_detect_zoom(self, mock_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "zoom.us", "exe": "/Applications/zoom.us.app/Contents/MacOS/zoom.us", "cmdline": []}
        mock_iter.return_value = [mock_proc]

        found, app = listen.detect_meeting_app()
        self.assertTrue(found)
        self.assertEqual(app, "zoom.us")

    @patch("psutil.process_iter")
    def test_detect_teams(self, mock_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "Microsoft Teams", "exe": "/Applications/Microsoft Teams.app", "cmdline": []}
        mock_iter.return_value = [mock_proc]

        found, app = listen.detect_meeting_app()
        self.assertTrue(found)
        self.assertEqual(app, "Microsoft Teams")

    @patch("psutil.process_iter")
    def test_detect_webex(self, mock_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "Cisco Webex Meetings", "exe": "/Applications/Cisco Webex Meetings.app", "cmdline": []}
        mock_iter.return_value = [mock_proc]

        found, app = listen.detect_meeting_app()
        self.assertTrue(found)
        self.assertEqual(app, "Cisco Webex Meetings")

    @patch("psutil.process_iter")
    def test_no_meeting_app(self, mock_iter):
        mock_proc = MagicMock()
        mock_proc.info = {"name": "python3", "exe": "/usr/bin/python3", "cmdline": ["python3", "listen.py"]}
        mock_iter.return_value = [mock_proc]

        found, app = listen.detect_meeting_app()
        self.assertFalse(found)
        self.assertIsNone(app)

    @patch("psutil.process_iter")
    def test_process_access_denied_handling(self, mock_iter):
        import psutil
        mock_proc_error = MagicMock()
        mock_proc_error.info.side_effect = psutil.AccessDenied()
        
        mock_proc_ok = MagicMock()
        mock_proc_ok.info = {"name": "zoom", "exe": "", "cmdline": []}
        mock_iter.return_value = [mock_proc_error, mock_proc_ok]

        found, app = listen.detect_meeting_app()
        self.assertTrue(found)
        self.assertEqual(app, "zoom")


class TestLifecycleEndpoints(unittest.TestCase):
    @patch("listener.listen.post_json")
    def test_start_and_end_lifecycle(self, mock_post):
        mock_post.return_value = {"status": "ok"}

        # 1. Start meeting
        meeting_id = listen.start_meeting_lifecycle(reason="Test meeting start")
        self.assertTrue(meeting_id.startswith("meeting-"))
        self.assertEqual(os.environ.get("MEETING_ID"), meeting_id)

        mock_post.assert_called_with(
            f"/meetings/{meeting_id}/start",
            {
                "title": unittest.mock.ANY,
                "status": "live",
                "startedAt": unittest.mock.ANY,
            }
        )

        # 2. Utterance
        listen.on_utterance("Hello world", meeting_id=meeting_id)
        mock_post.assert_called_with(
            f"/meetings/{meeting_id}/utterance",
            {
                "speaker": "Speaker",
                "text": "Hello world",
                "ts": unittest.mock.ANY,
            }
        )

        # 3. End meeting
        listen.end_meeting_lifecycle(meeting_id, reason="Test ended")
        mock_post.assert_called_with(f"/meetings/{meeting_id}/end", {})

    @patch("urllib.request.urlopen")
    def test_post_json_certifi_ssl(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        res = listen.post_json("/meetings/test-1/start", {"test": True})
        self.assertEqual(res, {"status": "ok"})
        mock_urlopen.assert_called_once()
        # Verify SSL context parameter is passed
        _, kwargs = mock_urlopen.call_args
        self.assertIn("context", kwargs)
        self.assertIsNotNone(kwargs["context"])


if __name__ == "__main__":
    unittest.main()
