import os
import sys
import time
import unittest
from unittest.mock import patch, MagicMock
import numpy as np

import listener.listen as listen


class TestListenerLifecycleIntegration(unittest.TestCase):
    """Simulates raw audio stream inputs to test listen_auto state machine transitions."""

    @patch("listener.listen.transcription_worker")
    @patch("webrtcvad.Vad")
    @patch("listener.listen.post_json")
    @patch("listener.listen.detect_meeting_app")
    @patch("sounddevice.InputStream")
    def test_sustained_speech_trigger_and_silence_end(
        self, mock_stream_cls, mock_detect_app, mock_post, mock_vad_cls, mock_worker
    ):
        # 1. Setup VAD mock
        mock_vad = MagicMock()
        speech_flag = [True]
        mock_vad.is_speech.side_effect = lambda raw_bytes, rate: speech_flag[0]
        mock_vad_cls.return_value = mock_vad

        # 2. Setup Post JSON mock
        posted_endpoints = []
        def mock_post_fn(endpoint, payload):
            posted_endpoints.append((endpoint, payload))
            return {"status": "ok"}
        mock_post.side_effect = mock_post_fn

        # No meeting app running
        mock_detect_app.return_value = (False, None)

        # 3. Simulate audio stream
        dummy_frame = np.zeros((listen.FRAME_SIZE, 1), dtype=np.int16)
        mock_stream = MagicMock()
        frame_count = 0
        simulated_time = [1000.0]

        def mock_time():
            return simulated_time[0]

        def stream_read(size):
            nonlocal frame_count
            frame_count += 1
            simulated_time[0] += 0.030

            # First 180 frames: speech (5.4s > 5.0s trigger)
            if frame_count <= 180:
                speech_flag[0] = True
                return (dummy_frame, False)
            # Next 30 frames: silence
            elif frame_count <= 210:
                speech_flag[0] = False
                return (dummy_frame, False)
            # Frame 211: advance time past 90s silence timeout
            elif frame_count == 211:
                speech_flag[0] = False
                simulated_time[0] += 95.0
                return (dummy_frame, False)
            else:
                raise KeyboardInterrupt()

        mock_stream.read.side_effect = stream_read
        mock_stream_cls.return_value.__enter__.return_value = mock_stream

        with patch("time.time", side_effect=mock_time):
            listen.listen_auto(device_index=0)

        endpoints_called = [ep for ep, _ in posted_endpoints]
        
        # 1. /start should have been called
        start_calls = [ep for ep in endpoints_called if ep.endswith("/start")]
        self.assertEqual(len(start_calls), 1)

        # 2. /end should have been called
        end_calls = [ep for ep in endpoints_called if ep.endswith("/end")]
        self.assertEqual(len(end_calls), 1)

    @patch("listener.listen.transcription_worker")
    @patch("webrtcvad.Vad")
    @patch("listener.listen.post_json")
    @patch("listener.listen.detect_meeting_app")
    @patch("sounddevice.InputStream")
    def test_meeting_app_trigger_and_app_close_end(
        self, mock_stream_cls, mock_detect_app, mock_post, mock_vad_cls, mock_worker
    ):
        mock_vad = MagicMock()
        mock_vad.is_speech.return_value = False
        mock_vad_cls.return_value = mock_vad

        posted_endpoints = []
        def mock_post_fn(endpoint, payload):
            posted_endpoints.append((endpoint, payload))
            return {"status": "ok"}
        mock_post.side_effect = mock_post_fn

        # App is Zoom at start, then closed
        app_state = [(True, "zoom.us")]

        def mock_detect():
            return app_state[0]
        mock_detect_app.side_effect = mock_detect

        dummy_frame = np.zeros((listen.FRAME_SIZE, 1), dtype=np.int16)
        mock_stream = MagicMock()
        read_count = 0
        simulated_time = [1000.0]

        def mock_time():
            return simulated_time[0]

        def stream_read(size):
            nonlocal read_count
            read_count += 1
            simulated_time[0] += 0.030

            if read_count == 1:
                # App detected on first poll
                simulated_time[0] += 5.0
                return (dummy_frame, False)
            elif read_count == 2:
                # Next poll: app closed
                app_state[0] = (False, None)
                simulated_time[0] += 5.0
                return (dummy_frame, False)
            else:
                raise KeyboardInterrupt()

        mock_stream.read.side_effect = stream_read
        mock_stream_cls.return_value.__enter__.return_value = mock_stream

        with patch("time.time", side_effect=mock_time):
            listen.listen_auto(device_index=0)

        endpoints_called = [ep for ep, _ in posted_endpoints]
        start_calls = [ep for ep in endpoints_called if ep.endswith("/start")]
        self.assertEqual(len(start_calls), 1)

        end_calls = [ep for ep in endpoints_called if ep.endswith("/end")]
        self.assertEqual(len(end_calls), 1)

    @patch("listener.listen.transcription_worker")
    @patch("webrtcvad.Vad")
    @patch("sounddevice.InputStream")
    def test_manual_mode_continuous_capture(
        self, mock_stream_cls, mock_vad_cls, mock_worker
    ):
        mock_vad = MagicMock()
        mock_vad.is_speech.return_value = False
        mock_vad_cls.return_value = mock_vad

        dummy_frame = np.zeros((listen.FRAME_SIZE, 1), dtype=np.int16)
        mock_stream = MagicMock()
        read_count = 0

        def stream_read(size):
            nonlocal read_count
            read_count += 1
            if read_count <= 3:
                return (dummy_frame, False)
            raise KeyboardInterrupt()

        mock_stream.read.side_effect = stream_read
        mock_stream_cls.return_value.__enter__.return_value = mock_stream

        # Run listen_manual
        listen.listen_manual(device_index=0)
        self.assertEqual(read_count, 4)


if __name__ == "__main__":
    unittest.main()

