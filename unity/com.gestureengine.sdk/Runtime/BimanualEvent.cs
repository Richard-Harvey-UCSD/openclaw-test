using System;

namespace GestureEngine
{
    /// <summary>
    /// Data for a two-hand gesture event (pinch_zoom, clap, frame, conducting).
    /// </summary>
    [Serializable]
    public class BimanualEvent
    {
        public string type;
        public string gesture;
        public float value;
        public float confidence;
        public double timestamp;

        public override string ToString()
        {
            return $"[Bimanual] {gesture} (value={value:F4}, confidence={confidence:F3})";
        }
    }
}
