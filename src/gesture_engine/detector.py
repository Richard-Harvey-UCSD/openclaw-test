"""Hand detection and landmark extraction using MediaPipe."""

import numpy as np

try:
    import mediapipe as mp
except ImportError:
    mp = None


class HandDetector:
    """Extracts 21 3D hand landmarks per hand using MediaPipe Hands.

    Each landmark is (x, y, z) normalized to [0, 1] relative to image dimensions.
    Returns up to `max_hands` detected hands per frame.
    """

    # MediaPipe hand landmark indices
    WRIST = 0
    THUMB_CMC, THUMB_MCP, THUMB_IP, THUMB_TIP = 1, 2, 3, 4
    INDEX_MCP, INDEX_PIP, INDEX_DIP, INDEX_TIP = 5, 6, 7, 8
    MIDDLE_MCP, MIDDLE_PIP, MIDDLE_DIP, MIDDLE_TIP = 9, 10, 11, 12
    RING_MCP, RING_PIP, RING_DIP, RING_TIP = 13, 14, 15, 16
    PINKY_MCP, PINKY_PIP, PINKY_DIP, PINKY_TIP = 17, 18, 19, 20

    NUM_LANDMARKS = 21
    LANDMARK_DIM = 3  # x, y, z

    def __init__(
        self,
        max_hands: int = 2,
        min_detection_confidence: float = 0.7,
        min_tracking_confidence: float = 0.5,
        static_image_mode: bool = False,
    ):
        if mp is None:
            raise ImportError(
                "mediapipe is required. Install with: pip install mediapipe"
            )

        self.max_hands = max_hands
        self._hands = mp.solutions.hands.Hands(
            static_image_mode=static_image_mode,
            max_num_hands=max_hands,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence,
        )

    def detect(self, frame_rgb: np.ndarray) -> list[np.ndarray]:
        """Detect hands and return landmark arrays.

        Args:
            frame_rgb: RGB image as numpy array (H, W, 3), uint8.

        Returns:
            List of landmark arrays, each shape (21, 3).
            Empty list if no hands detected.
        """
        results = self._hands.process(frame_rgb)

        if not results.multi_hand_landmarks:
            return []

        hands = []
        for hand_landmarks in results.multi_hand_landmarks:
            landmarks = np.array(
                [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark],
                dtype=np.float32,
            )
            hands.append(landmarks)

        return hands

    def detect_normalized(self, frame_rgb: np.ndarray) -> list[np.ndarray]:
        """Detect hands and return wrist-centered, scale-normalized landmarks.

        Landmarks are translated so wrist is at origin, then scaled so the
        max distance from wrist is 1.0. This makes features invariant to
        hand position and distance from camera.

        Returns:
            List of normalized landmark arrays, each shape (21, 3).
        """
        raw_hands = self.detect(frame_rgb)
        normalized = []

        for landmarks in raw_hands:
            centered = landmarks - landmarks[self.WRIST]
            scale = np.max(np.linalg.norm(centered, axis=1)) + 1e-8
            normalized.append(centered / scale)

        return normalized

    def close(self):
        """Release MediaPipe resources."""
        self._hands.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
