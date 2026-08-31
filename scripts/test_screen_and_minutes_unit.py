import os
import sys
import unittest
import tempfile
from PIL import Image, ImageDraw
import imagehash

from understudy_agent.schemas import (
    ScreenContext,
    TopicNote,
    Minutes,
)
from understudy_agent.screen_analyzer import analyze_screenshot, get_mock_screen_context
from understudy_agent.minutes import generate_minutes, get_mock_minutes
from understudy_agent import ledger
from listener.screen_watcher import downscale_image, DEFAULT_THRESHOLD

class TestScreenAndMinutes(unittest.TestCase):
    def setUp(self):
        os.environ["FIRESTORE_EMULATOR_HOST"] = "127.0.0.1:8080"
        os.environ["GOOGLE_CLOUD_PROJECT"] = "demo-understudy"

    def test_schemas_validation(self):
        ctx = ScreenContext(
            kind="website",
            summary="Browsing GitHub repository for Understudy project",
            keyPoints=["Viewing pull requests", "Checking CI status"],
            ts="14:30:00",
        )
        self.assertEqual(ctx.kind, "website")
        self.assertEqual(len(ctx.keyPoints), 2)
        json_data = ctx.model_dump()
        self.assertEqual(json_data["keyPoints"], ["Viewing pull requests", "Checking CI status"])

        topic = TopicNote(heading="Frontend Roadmap", notes="Discussed Q3 milestones and deliverables.")
        self.assertEqual(topic.heading, "Frontend Roadmap")

        minutes = Minutes(
            title="Design Review",
            date="Aug 27",
            attendees=["Alex", "Sam"],
            topics=[topic],
            decisions=["Approved navigation redesign"],
            materialsShown=["Figma mockup"],
            actionItems=[{"id": "ai-1", "text": "Update styles", "category": "doc", "assignee": "Alex", "due": "tomorrow"}],
        )
        self.assertEqual(minutes.title, "Design Review")
        self.assertEqual(len(minutes.topics), 1)
        self.assertEqual(len(minutes.decisions), 1)

    def test_downscale_image(self):
        # Large image: 2560 x 1440
        large_img = Image.new("RGB", (2560, 1440), color="blue")
        resized = downscale_image(large_img, max_width=1280)
        self.assertEqual(resized.width, 1280)
        self.assertEqual(resized.height, 720)

        # Small image: 800 x 600 -> should remain unchanged
        small_img = Image.new("RGB", (800, 600), color="red")
        kept = downscale_image(small_img, max_width=1280)
        self.assertEqual(kept.width, 800)
        self.assertEqual(kept.height, 600)

    def test_perceptual_hash_change_detection(self):
        # 1. Identical frames
        img1 = Image.new("RGB", (640, 480), color="white")
        img2 = Image.new("RGB", (640, 480), color="white")
        h1 = imagehash.phash(img1)
        h2 = imagehash.phash(img2)
        distance_same = h1 - h2
        self.assertEqual(distance_same, 0)
        self.assertTrue(distance_same <= DEFAULT_THRESHOLD)

        # 2. Visually distinct frame (e.g. black background with heavy text/shapes)
        img3 = Image.new("RGB", (640, 480), color="black")
        draw = ImageDraw.Draw(img3)
        draw.rectangle([50, 50, 400, 400], fill="white")
        draw.line([0, 0, 640, 480], fill="red", width=10)
        h3 = imagehash.phash(img3)
        distance_diff = h1 - h3
        self.assertTrue(distance_diff > DEFAULT_THRESHOLD, f"Distance {distance_diff} should exceed threshold {DEFAULT_THRESHOLD}")

    def test_analyze_screenshot_mock(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        try:
            img = Image.new("RGB", (200, 200), color="gray")
            img.save(tmp_path, format="PNG")
            ctx = analyze_screenshot(tmp_path, mock=True)
            self.assertIsInstance(ctx, ScreenContext)
            self.assertEqual(ctx.kind, "slide")
            self.assertTrue(len(ctx.keyPoints) > 0)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_ledger_screen_context_and_minutes(self):
        meeting_id = "test-unit-meeting"
        ledger.create_meeting(meeting_id, title="Unit Test Meeting", date="Aug 27")

        # Test add_screen_context & get_screen_context
        ctx = ScreenContext(
            kind="code",
            summary="Reviewing pull request #42 in VS Code",
            keyPoints=["Refactored auth module", "Added unit tests"],
            ts="10:00:00",
        )
        saved_ctx = ledger.add_screen_context(meeting_id, ctx)
        self.assertIn("id", saved_ctx)
        self.assertEqual(saved_ctx["kind"], "code")

        all_ctx = ledger.get_screen_context(meeting_id)
        self.assertTrue(len(all_ctx) >= 1)
        self.assertTrue(any(c.get("summary") == ctx.summary for c in all_ctx))

        # Test save_minutes & get_minutes
        mock_min = get_mock_minutes(meeting_id, meeting_title="Unit Test Meeting", meeting_date="Aug 27")
        ledger.save_minutes(meeting_id, mock_min)

        retrieved_min = ledger.get_minutes(meeting_id)
        self.assertIsNotNone(retrieved_min)
        self.assertEqual(retrieved_min.get("title"), "Unit Test Meeting")
        self.assertEqual(len(retrieved_min.get("topics", [])), len(mock_min.topics))

        # Test generate_minutes mock
        gen_min = generate_minutes(meeting_id, mock=True)
        self.assertIsInstance(gen_min, Minutes)
        self.assertEqual(gen_min.title, "Unit Test Meeting")

if __name__ == "__main__":
    unittest.main()
