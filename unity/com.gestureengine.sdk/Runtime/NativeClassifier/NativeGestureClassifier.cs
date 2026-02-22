using UnityEngine;

namespace GestureEngine.NativeClassifier
{
    /// <summary>
    /// Standalone gesture classifier that runs entirely in C# — no Python server needed.
    /// Uses the same rule-based approach as the Python GestureClassifier.
    /// </summary>
    public class NativeGestureClassifier
    {
        private GestureRegistry _registry;

        public NativeGestureClassifier(GestureRegistry registry = null)
        {
            _registry = registry ?? GestureRegistry.WithDefaults();
        }

        /// <summary>
        /// Load gesture definitions from JSON (cross-platform with Python format).
        /// </summary>
        public void LoadDefinitions(string json)
        {
            _registry = new GestureRegistry();
            _registry.LoadFromJson(json);
        }

        /// <summary>
        /// Classify a gesture from 21 hand landmarks.
        /// </summary>
        /// <param name="landmarks">21 Vector3 landmarks.</param>
        /// <param name="gestureName">Output: matched gesture name, or null.</param>
        /// <param name="confidence">Output: confidence score.</param>
        /// <returns>True if a gesture was recognized.</returns>
        public bool Classify(Vector3[] landmarks, out string gestureName, out float confidence)
        {
            return _registry.Match(landmarks, out gestureName, out confidence);
        }

        /// <summary>
        /// Classify from a flat float array (63 values = 21 * 3).
        /// </summary>
        public bool Classify(float[] flatLandmarks, out string gestureName, out float confidence)
        {
            gestureName = null;
            confidence = 0f;

            if (flatLandmarks == null || flatLandmarks.Length < 63)
                return false;

            var landmarks = new Vector3[21];
            for (int i = 0; i < 21; i++)
            {
                landmarks[i] = new Vector3(
                    flatLandmarks[i * 3],
                    flatLandmarks[i * 3 + 1],
                    flatLandmarks[i * 3 + 2]
                );
            }

            return Classify(landmarks, out gestureName, out confidence);
        }

        /// <summary>
        /// Extract the 81-dimensional feature vector (for ML pipelines).
        /// </summary>
        public float[] ExtractFeatures(Vector3[] landmarks)
        {
            return FeatureExtractor.Extract(landmarks);
        }

        public GestureRegistry Registry => _registry;
    }
}
