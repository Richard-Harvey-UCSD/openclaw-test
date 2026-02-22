using UnityEngine;

namespace GestureEngine
{
    /// <summary>
    /// ScriptableObject for GestureEngine configuration.
    /// Create via Assets → Create → GestureEngine → Config.
    /// </summary>
    [CreateAssetMenu(fileName = "GestureEngineConfig", menuName = "GestureEngine/Config")]
    public class GestureConfig : ScriptableObject
    {
        [Header("Connection")]
        [Tooltip("WebSocket server URL")]
        public string serverUrl = "ws://localhost:8765/ws";

        [Tooltip("Automatically connect on Start")]
        public bool autoConnect = true;

        [Tooltip("Reconnect automatically on disconnect")]
        public bool autoReconnect = true;

        [Tooltip("Seconds between reconnect attempts")]
        [Range(0.5f, 30f)]
        public float reconnectInterval = 3f;

        [Tooltip("Maximum reconnect attempts (0 = unlimited)")]
        public int maxReconnectAttempts = 0;

        [Header("Filtering")]
        [Tooltip("Global minimum confidence threshold")]
        [Range(0f, 1f)]
        public float minimumConfidence = 0.6f;

        [Tooltip("Global cooldown between same gesture events (seconds)")]
        [Range(0f, 5f)]
        public float gestureCooldown = 0.3f;

        [Header("Debug")]
        [Tooltip("Enable debug visualization of hand landmarks")]
        public bool debugVisualization = false;

        [Tooltip("Log all incoming events to console")]
        public bool logEvents = false;

        [Header("Native Classifier")]
        [Tooltip("Use native C# classifier instead of server")]
        public bool useNativeClassifier = false;
    }
}
