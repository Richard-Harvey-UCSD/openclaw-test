using System;
using UnityEngine;

namespace GestureEngine.NativeClassifier
{
    /// <summary>
    /// A gesture defined by finger states and optional geometric constraints.
    /// C# port of the Python GestureDefinition class.
    /// </summary>
    [Serializable]
    public class GestureDefinition
    {
        public string name;
        public FingerState thumb = FingerState.Any;
        public FingerState index = FingerState.Any;
        public FingerState middle = FingerState.Any;
        public FingerState ring = FingerState.Any;
        public FingerState pinky = FingerState.Any;
        public float minConfidence = 0.6f;
        public Constraint[] constraints;

        private static readonly int[] FingerTips = { 4, 8, 12, 16, 20 };
        private static readonly int[] FingerPIPs = { 3, 6, 10, 14, 18 };
        private const int Wrist = 0;

        /// <summary>
        /// Check if landmarks match this gesture definition.
        /// </summary>
        /// <param name="landmarks">21 landmark positions.</param>
        /// <param name="confidence">Output confidence score.</param>
        /// <returns>True if matched.</returns>
        public bool Match(Vector3[] landmarks, out float confidence)
        {
            var fingerStates = GetFingerStates(landmarks);
            var expected = new[] { thumb, index, middle, ring, pinky };

            int matches = 0;
            int checked_ = 0;

            for (int i = 0; i < 5; i++)
            {
                if (expected[i] == FingerState.Any) continue;
                checked_++;
                if (fingerStates[i] == expected[i]) matches++;
            }

            float fingerConf = checked_ == 0 ? 1f : (float)matches / checked_;
            float constraintScore = CheckConstraints(landmarks);

            confidence = (constraints != null && constraints.Length > 0)
                ? 0.7f * fingerConf + 0.3f * constraintScore
                : fingerConf;

            return confidence >= minConfidence;
        }

        private FingerState[] GetFingerStates(Vector3[] landmarks)
        {
            var states = new FingerState[5];
            Vector3 wrist = landmarks[Wrist];

            for (int i = 0; i < 5; i++)
            {
                float tipDist = Vector3.Distance(landmarks[FingerTips[i]], wrist);
                float pipDist = Vector3.Distance(landmarks[FingerPIPs[i]], wrist);
                states[i] = tipDist > pipDist ? FingerState.Extended : FingerState.Curled;
            }

            return states;
        }

        private float CheckConstraints(Vector3[] landmarks)
        {
            if (constraints == null || constraints.Length == 0) return 1f;

            float total = 0f;
            foreach (var c in constraints)
            {
                if (c.type == "distance")
                {
                    float dist = Vector3.Distance(landmarks[c.landmarkA], landmarks[c.landmarkB]);
                    total += (dist >= c.min && dist <= c.max) ? 1f : 0f;
                }
                else if (c.type == "angle")
                {
                    Vector3 ba = landmarks[c.landmarkA] - landmarks[c.landmarkB];
                    Vector3 bc = landmarks[c.landmarkC] - landmarks[c.landmarkB];
                    float cosAngle = Vector3.Dot(ba.normalized, bc.normalized);
                    float angle = Mathf.Acos(Mathf.Clamp(cosAngle, -1f, 1f)) * Mathf.Rad2Deg;
                    total += (angle >= c.minAngle && angle <= c.maxAngle) ? 1f : 0f;
                }
            }

            return total / constraints.Length;
        }
    }

    /// <summary>
    /// Geometric constraint for gesture matching.
    /// </summary>
    [Serializable]
    public class Constraint
    {
        public string type; // "distance" or "angle"
        public int landmarkA;
        public int landmarkB;
        public int landmarkC; // for angle: vertex is B, angle at A-B-C
        public float min;
        public float max = float.MaxValue;
        public float minAngle;
        public float maxAngle = 180f;
    }
}
