using System;

namespace GestureEngine
{
    /// <summary>
    /// Data for a spatial trajectory event (swipe, circle, etc.).
    /// </summary>
    [Serializable]
    public class TrajectoryEvent
    {
        public string type;
        public string name;
        public float score;
        public int hand_id;
        public float duration;
        public double timestamp;

        public override string ToString()
        {
            return $"[Trajectory] {name} (score={score:F3}, duration={duration:F3}s)";
        }
    }
}
