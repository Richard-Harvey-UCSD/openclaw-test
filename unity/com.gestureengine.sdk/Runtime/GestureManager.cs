using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Events;

namespace GestureEngine
{
    /// <summary>
    /// Main entry point for GestureEngine in Unity.
    /// Singleton MonoBehaviour that manages the WebSocket connection
    /// and dispatches gesture events via UnityEvents.
    /// </summary>
    public class GestureManager : MonoBehaviour
    {
        #region Singleton

        private static GestureManager _instance;

        public static GestureManager Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = FindObjectOfType<GestureManager>();
                    if (_instance == null)
                    {
                        var go = new GameObject("GestureManager");
                        _instance = go.AddComponent<GestureManager>();
                    }
                }
                return _instance;
            }
        }

        #endregion

        #region Inspector Fields

        [Header("Configuration")]
        [SerializeField] private GestureConfig config;

        [Header("Connection (override config)")]
        [SerializeField] private string serverUrl = "ws://localhost:8765/ws";
        [SerializeField] private bool autoConnect = true;
        [SerializeField] private bool autoReconnect = true;
        [SerializeField] [Range(0.5f, 30f)] private float reconnectInterval = 3f;

        [Header("Filtering")]
        [SerializeField] [Range(0f, 1f)] private float minimumConfidence = 0.6f;
        [SerializeField] [Range(0f, 5f)] private float gestureCooldown = 0.3f;

        [Header("Debug")]
        [SerializeField] private bool debugVisualization;
        [SerializeField] private bool logEvents;

        [Header("Events")]
        public GestureUnityEvent OnGesture = new GestureUnityEvent();
        public SequenceUnityEvent OnSequence = new SequenceUnityEvent();
        public BimanualUnityEvent OnBimanual = new BimanualUnityEvent();
        public TrajectoryUnityEvent OnTrajectory = new TrajectoryUnityEvent();
        public HandUpdateUnityEvent OnHandUpdate = new HandUpdateUnityEvent();
        public UnityEvent OnConnectedEvent = new UnityEvent();
        public StringUnityEvent OnDisconnectedEvent = new StringUnityEvent();

        #endregion

        #region Public API

        public bool IsConnected => _client != null && _client.IsConnected;

        public string[] AvailableGestures { get; private set; } = Array.Empty<string>();
        public string[] AvailableTrajectories { get; private set; } = Array.Empty<string>();

        /// <summary>Connect to the GestureEngine server.</summary>
        public void Connect()
        {
            if (_client != null && _client.IsConnected) return;

            InitClient();
            _client.Connect();
        }

        /// <summary>Disconnect from the server.</summary>
        public void Disconnect()
        {
            _client?.Disconnect();
        }

        /// <summary>
        /// Register a callback for a specific gesture by name.
        /// </summary>
        public void RegisterGesture(string gestureName, Action<GestureEvent> callback)
        {
            if (!_gestureCallbacks.ContainsKey(gestureName))
                _gestureCallbacks[gestureName] = new List<Action<GestureEvent>>();
            _gestureCallbacks[gestureName].Add(callback);
        }

        /// <summary>
        /// Unregister a callback for a specific gesture.
        /// </summary>
        public void UnregisterGesture(string gestureName, Action<GestureEvent> callback)
        {
            if (_gestureCallbacks.TryGetValue(gestureName, out var list))
                list.Remove(callback);
        }

        /// <summary>Get the hand model for a given hand index.</summary>
        public HandModel GetHand(int index)
        {
            if (_hands.TryGetValue(index, out var hand))
                return hand;
            return null;
        }

        #endregion

        #region Private

        private GestureEngineClient _client;
        private Dictionary<string, List<Action<GestureEvent>>> _gestureCallbacks
            = new Dictionary<string, List<Action<GestureEvent>>>();
        private Dictionary<int, HandModel> _hands = new Dictionary<int, HandModel>();
        private Dictionary<string, float> _lastGestureTime = new Dictionary<string, float>();
        private GestureVisualizer _visualizer;

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }

            _instance = this;
            DontDestroyOnLoad(gameObject);
            ApplyConfig();
        }

        private void Start()
        {
            if (autoConnect)
                Connect();
        }

        private void Update()
        {
            if (_client == null) return;

            // Process all queued messages on main thread
            while (_client.IncomingMessages.TryDequeue(out var json))
            {
                ProcessMessage(json);
            }
        }

        private void OnDestroy()
        {
            _client?.Dispose();
            _client = null;
            if (_instance == this)
                _instance = null;
        }

        private void ApplyConfig()
        {
            if (config != null)
            {
                serverUrl = config.serverUrl;
                autoConnect = config.autoConnect;
                autoReconnect = config.autoReconnect;
                reconnectInterval = config.reconnectInterval;
                minimumConfidence = config.minimumConfidence;
                gestureCooldown = config.gestureCooldown;
                debugVisualization = config.debugVisualization;
                logEvents = config.logEvents;
            }
        }

        private void InitClient()
        {
            _client?.Dispose();
            _client = new GestureEngineClient
            {
                ServerUrl = serverUrl,
                AutoReconnect = autoReconnect,
                ReconnectInterval = reconnectInterval,
            };

            _client.OnConnected += () =>
            {
                // Queue for main thread
                _client.IncomingMessages.Enqueue("{\"type\":\"_internal_connected\"}");
            };

            _client.OnDisconnected += (reason) =>
            {
                _client.IncomingMessages.Enqueue(
                    $"{{\"type\":\"_internal_disconnected\",\"reason\":\"{reason}\"}}");
            };
        }

        private void ProcessMessage(string json)
        {
            try
            {
                // Peek at type field for routing
                string msgType = ExtractType(json);

                switch (msgType)
                {
                    case "_internal_connected":
                        OnConnectedEvent?.Invoke();
                        if (logEvents) Debug.Log("[GestureEngine] Connected");
                        break;

                    case "_internal_disconnected":
                        OnDisconnectedEvent?.Invoke("Connection lost");
                        if (logEvents) Debug.Log("[GestureEngine] Disconnected");
                        break;

                    case "connected":
                        var connEvt = JsonUtility.FromJson<ConnectedEvent>(json);
                        AvailableGestures = connEvt.gestures ?? Array.Empty<string>();
                        AvailableTrajectories = connEvt.trajectories ?? Array.Empty<string>();
                        if (logEvents) Debug.Log($"[GestureEngine] Server reports {AvailableGestures.Length} gestures");
                        break;

                    case "gesture":
                        var gestureEvt = JsonUtility.FromJson<GestureEvent>(json);
                        HandleGesture(gestureEvt);
                        break;

                    case "sequence":
                        var seqEvt = JsonUtility.FromJson<GestureSequenceEvent>(json);
                        if (logEvents) Debug.Log(seqEvt);
                        OnSequence?.Invoke(seqEvt);
                        break;

                    case "bimanual":
                        var biEvt = JsonUtility.FromJson<BimanualEvent>(json);
                        if (logEvents) Debug.Log(biEvt);
                        OnBimanual?.Invoke(biEvt);
                        break;

                    case "trajectory":
                        var trajEvt = JsonUtility.FromJson<TrajectoryEvent>(json);
                        if (logEvents) Debug.Log(trajEvt);
                        OnTrajectory?.Invoke(trajEvt);
                        break;

                    case "hand_update":
                        var handEvt = JsonUtility.FromJson<HandUpdateEvent>(json);
                        HandleHandUpdate(handEvt);
                        break;

                    case "stats":
                        // Silently consume stats
                        break;

                    case "ping":
                        _client?.Send("{\"type\":\"pong\"}");
                        break;
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[GestureEngine] Failed to parse message: {ex.Message}");
            }
        }

        private void HandleGesture(GestureEvent evt)
        {
            if (evt.confidence < minimumConfidence)
                return;

            // Cooldown check
            string key = $"{evt.gesture}_{evt.hand_index}";
            if (_lastGestureTime.TryGetValue(key, out float lastTime))
            {
                if (Time.time - lastTime < gestureCooldown)
                    return;
            }
            _lastGestureTime[key] = Time.time;

            if (logEvents) Debug.Log(evt);
            OnGesture?.Invoke(evt);

            // Named callbacks
            if (_gestureCallbacks.TryGetValue(evt.gesture, out var callbacks))
            {
                foreach (var cb in callbacks)
                {
                    try { cb(evt); }
                    catch (Exception ex) { Debug.LogException(ex); }
                }
            }
        }

        private void HandleHandUpdate(HandUpdateEvent evt)
        {
            if (!_hands.TryGetValue(evt.hand_index, out var hand))
            {
                hand = new HandModel { HandIndex = evt.hand_index };
                _hands[evt.hand_index] = hand;
            }

            hand.UpdateFromFlatArray(evt.landmarks, evt.timestamp);
            OnHandUpdate?.Invoke(evt);

            // Update visualizer
            if (debugVisualization)
            {
                if (_visualizer == null)
                {
                    _visualizer = GetComponent<GestureVisualizer>();
                    if (_visualizer == null)
                        _visualizer = gameObject.AddComponent<GestureVisualizer>();
                }
                _visualizer.UpdateHand(hand);
            }
        }

        /// <summary>
        /// Lightweight JSON type extraction without full parse.
        /// </summary>
        private static string ExtractType(string json)
        {
            // Find "type":"value" or "type": "value"
            int idx = json.IndexOf("\"type\"", StringComparison.Ordinal);
            if (idx < 0) return "";

            idx = json.IndexOf(':', idx + 6);
            if (idx < 0) return "";

            int start = json.IndexOf('"', idx + 1);
            if (start < 0) return "";

            int end = json.IndexOf('"', start + 1);
            if (end < 0) return "";

            return json.Substring(start + 1, end - start - 1);
        }

        #endregion

        #region UnityEvent Types

        [Serializable] public class GestureUnityEvent : UnityEvent<GestureEvent> { }
        [Serializable] public class SequenceUnityEvent : UnityEvent<GestureSequenceEvent> { }
        [Serializable] public class BimanualUnityEvent : UnityEvent<BimanualEvent> { }
        [Serializable] public class TrajectoryUnityEvent : UnityEvent<TrajectoryEvent> { }
        [Serializable] public class HandUpdateUnityEvent : UnityEvent<HandUpdateEvent> { }
        [Serializable] public class StringUnityEvent : UnityEvent<string> { }

        #endregion
    }
}
