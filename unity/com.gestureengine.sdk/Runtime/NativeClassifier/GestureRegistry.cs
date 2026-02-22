using System.Collections.Generic;
using UnityEngine;

namespace GestureEngine.NativeClassifier
{
    /// <summary>
    /// Registry of gesture definitions with matching logic.
    /// C# port of the Python GestureRegistry.
    /// </summary>
    public class GestureRegistry
    {
        private readonly List<GestureDefinition> _gestures = new List<GestureDefinition>();

        public IReadOnlyList<GestureDefinition> Gestures => _gestures;

        public void Register(GestureDefinition gesture)
        {
            _gestures.Add(gesture);
        }

        /// <summary>
        /// Find the best matching gesture for given landmarks.
        /// </summary>
        /// <param name="landmarks">21 hand landmarks.</param>
        /// <param name="gestureName">Output: matched gesture name.</param>
        /// <param name="confidence">Output: match confidence.</param>
        /// <returns>True if any gesture matched.</returns>
        public bool Match(Vector3[] landmarks, out string gestureName, out float confidence)
        {
            gestureName = null;
            confidence = 0f;

            foreach (var g in _gestures)
            {
                if (g.Match(landmarks, out float conf))
                {
                    if (conf > confidence)
                    {
                        confidence = conf;
                        gestureName = g.name;
                    }
                }
            }

            return gestureName != null;
        }

        /// <summary>
        /// Load gesture definitions from a JSON string (same format as Python).
        /// Expected format: { "gestures": [ { "name": "...", "fingers": { ... }, ... } ] }
        /// </summary>
        public void LoadFromJson(string json)
        {
            var wrapper = JsonUtility.FromJson<GestureFileWrapper>(json);
            if (wrapper?.gestures == null) return;

            foreach (var entry in wrapper.gestures)
            {
                var def = new GestureDefinition
                {
                    name = entry.name,
                    minConfidence = entry.min_confidence > 0 ? entry.min_confidence : 0.6f,
                    thumb = ParseFingerState(entry.fingers?.thumb),
                    index = ParseFingerState(entry.fingers?.index),
                    middle = ParseFingerState(entry.fingers?.middle),
                    ring = ParseFingerState(entry.fingers?.ring),
                    pinky = ParseFingerState(entry.fingers?.pinky),
                };

                if (entry.constraints != null)
                {
                    var constraints = new List<Constraint>();
                    foreach (var c in entry.constraints)
                    {
                        var constraint = new Constraint
                        {
                            type = c.type,
                            min = c.min,
                            max = c.max > 0 ? c.max : float.MaxValue,
                            minAngle = c.min_angle,
                            maxAngle = c.max_angle > 0 ? c.max_angle : 180f,
                        };
                        if (c.landmarks != null && c.landmarks.Length >= 2)
                        {
                            constraint.landmarkA = c.landmarks[0];
                            constraint.landmarkB = c.landmarks[1];
                            if (c.landmarks.Length >= 3)
                                constraint.landmarkC = c.landmarks[2];
                        }
                        constraints.Add(constraint);
                    }
                    def.constraints = constraints.ToArray();
                }

                Register(def);
            }
        }

        private static FingerState ParseFingerState(string value)
        {
            if (value == null) return FingerState.Any;
            switch (value.ToLowerInvariant())
            {
                case "extended": return FingerState.Extended;
                case "curled": return FingerState.Curled;
                default: return FingerState.Any;
            }
        }

        /// <summary>
        /// Create a registry with the 7 built-in gestures (same as Python defaults).
        /// </summary>
        public static GestureRegistry WithDefaults()
        {
            var reg = new GestureRegistry();

            reg.Register(new GestureDefinition
            {
                name = "open_hand",
                thumb = FingerState.Extended, index = FingerState.Extended,
                middle = FingerState.Extended, ring = FingerState.Extended,
                pinky = FingerState.Extended
            });

            reg.Register(new GestureDefinition
            {
                name = "fist",
                thumb = FingerState.Curled, index = FingerState.Curled,
                middle = FingerState.Curled, ring = FingerState.Curled,
                pinky = FingerState.Curled
            });

            reg.Register(new GestureDefinition
            {
                name = "thumbs_up",
                thumb = FingerState.Extended, index = FingerState.Curled,
                middle = FingerState.Curled, ring = FingerState.Curled,
                pinky = FingerState.Curled
            });

            reg.Register(new GestureDefinition
            {
                name = "peace",
                thumb = FingerState.Curled, index = FingerState.Extended,
                middle = FingerState.Extended, ring = FingerState.Curled,
                pinky = FingerState.Curled
            });

            reg.Register(new GestureDefinition
            {
                name = "pointing",
                thumb = FingerState.Curled, index = FingerState.Extended,
                middle = FingerState.Curled, ring = FingerState.Curled,
                pinky = FingerState.Curled
            });

            reg.Register(new GestureDefinition
            {
                name = "rock_on",
                thumb = FingerState.Curled, index = FingerState.Extended,
                middle = FingerState.Curled, ring = FingerState.Curled,
                pinky = FingerState.Extended
            });

            reg.Register(new GestureDefinition
            {
                name = "ok_sign",
                thumb = FingerState.Extended, index = FingerState.Extended,
                middle = FingerState.Extended, ring = FingerState.Extended,
                pinky = FingerState.Extended,
                minConfidence = 0.5f,
                constraints = new[]
                {
                    new Constraint { type = "distance", landmarkA = 4, landmarkB = 8, min = 0f, max = 0.15f }
                }
            });

            return reg;
        }

        #region JSON Deserialization Types

        [System.Serializable]
        private class GestureFileWrapper
        {
            public GestureJsonEntry[] gestures;
        }

        [System.Serializable]
        private class GestureJsonEntry
        {
            public string name;
            public float min_confidence;
            public FingerJson fingers;
            public ConstraintJson[] constraints;
        }

        [System.Serializable]
        private class FingerJson
        {
            public string thumb;
            public string index;
            public string middle;
            public string ring;
            public string pinky;
        }

        [System.Serializable]
        private class ConstraintJson
        {
            public string type;
            public int[] landmarks;
            public float min;
            public float max;
            public float min_angle;
            public float max_angle;
        }

        #endregion
    }
}
