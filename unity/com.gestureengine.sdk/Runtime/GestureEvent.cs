using System;
using UnityEngine;

namespace GestureEngine
{
    /// <summary>
    /// Data for a single gesture recognition event from the server.
    /// </summary>
    [Serializable]
    public class GestureEvent
    {
        public string type;
        public string gesture;
        public float confidence;
        public int hand_index;
        public double timestamp;
        public float latency_ms;

        public override string ToString()
        {
            return $"[Gesture] {gesture} (confidence={confidence:F3}, hand={hand_index})";
        }
    }

    /// <summary>
    /// Hand landmark update with 21 3D points.
    /// </summary>
    [Serializable]
    public class HandUpdateEvent
    {
        public string type;
        public int hand_index;
        public float[] landmarks; // flattened 21*3 = 63 floats
        public double timestamp;

        /// <summary>
        /// Get landmark at index (0-20) as a Vector3.
        /// </summary>
        public Vector3 GetLandmark(int index)
        {
            if (landmarks == null || index < 0 || index > 20)
                return Vector3.zero;
            int i = index * 3;
            if (i + 2 >= landmarks.Length)
                return Vector3.zero;
            return new Vector3(landmarks[i], landmarks[i + 1], landmarks[i + 2]);
        }
    }

    /// <summary>
    /// Server statistics update.
    /// </summary>
    [Serializable]
    public class StatsEvent
    {
        public string type;
        public float fps;
        public float latency_ms;
        public int hands_detected;
    }

    /// <summary>
    /// Connection acknowledgement from server.
    /// </summary>
    [Serializable]
    public class ConnectedEvent
    {
        public string type;
        public string[] gestures;
        public string[] trajectories;
    }
}
