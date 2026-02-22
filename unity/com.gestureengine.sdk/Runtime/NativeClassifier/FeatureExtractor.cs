using UnityEngine;

namespace GestureEngine.NativeClassifier
{
    /// <summary>
    /// Extracts the 81-dimensional feature vector from hand landmarks.
    /// C# port of GestureClassifier.extract_features() from Python.
    /// </summary>
    public static class FeatureExtractor
    {
        private static readonly int[] Tips = { 4, 8, 12, 16, 20 };
        private static readonly int[] PIPs = { 3, 6, 10, 14, 18 };

        /// <summary>
        /// Extract 81-dimensional feature vector from 21 hand landmarks.
        /// Features: 63 raw positions + 10 fingertip distances + 5 extension ratios + 3 palm normal.
        /// </summary>
        public static float[] Extract(Vector3[] landmarks)
        {
            var features = new float[81];
            int idx = 0;

            // Raw landmark positions (63 features)
            for (int i = 0; i < 21; i++)
            {
                features[idx++] = landmarks[i].x;
                features[idx++] = landmarks[i].y;
                features[idx++] = landmarks[i].z;
            }

            // Pairwise fingertip distances (10 features)
            for (int i = 0; i < Tips.Length; i++)
            {
                for (int j = i + 1; j < Tips.Length; j++)
                {
                    features[idx++] = Vector3.Distance(landmarks[Tips[i]], landmarks[Tips[j]]);
                }
            }

            // Finger extension ratios: tip_dist / pip_dist from wrist (5 features)
            Vector3 wrist = landmarks[0];
            for (int i = 0; i < 5; i++)
            {
                float tipDist = Vector3.Distance(landmarks[Tips[i]], wrist);
                float pipDist = Vector3.Distance(landmarks[PIPs[i]], wrist) + 1e-8f;
                features[idx++] = tipDist / pipDist;
            }

            // Palm orientation: normal vector of palm triangle (3 features)
            Vector3 v1 = landmarks[5] - landmarks[0];  // wrist → index_mcp
            Vector3 v2 = landmarks[17] - landmarks[0]; // wrist → pinky_mcp
            Vector3 palmNormal = Vector3.Cross(v1, v2);
            float norm = palmNormal.magnitude + 1e-8f;
            palmNormal /= norm;

            features[idx++] = palmNormal.x;
            features[idx++] = palmNormal.y;
            features[idx++] = palmNormal.z;

            return features;
        }
    }
}
