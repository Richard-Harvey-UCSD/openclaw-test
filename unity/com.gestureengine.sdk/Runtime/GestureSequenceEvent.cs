using System;

namespace GestureEngine
{
    /// <summary>
    /// Data for a gesture sequence event (e.g., fist → open_hand = "release").
    /// </summary>
    [Serializable]
    public class GestureSequenceEvent
    {
        public string type;
        public string sequence;
        public string[] gestures;
        public float duration;
        public double timestamp;

        public override string ToString()
        {
            string steps = gestures != null ? string.Join(" → ", gestures) : "";
            return $"[Sequence] {sequence} ({steps}, duration={duration:F3}s)";
        }
    }
}
