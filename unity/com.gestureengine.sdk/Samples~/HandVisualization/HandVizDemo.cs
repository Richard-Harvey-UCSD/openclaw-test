using UnityEngine;
using GestureEngine;

/// <summary>
/// Demo that visualizes hand landmarks in 3D space.
/// Add this to a scene with a GestureManager to see hands rendered.
/// </summary>
public class HandVizDemo : MonoBehaviour
{
    [Header("Visualization")]
    [SerializeField] private float handScale = 2f;
    [SerializeField] private Vector3 handOffset = new Vector3(0, 1.5f, 2f);

    [Header("UI")]
    [SerializeField] private bool showGestureLabel = true;

    private GestureVisualizer _visualizer;
    private string _currentGesture = "";
    private float _currentConfidence;

    private void Start()
    {
        // Ensure GestureManager exists
        var gm = GestureManager.Instance;

        // Add visualizer
        _visualizer = gameObject.AddComponent<GestureVisualizer>();

        // Listen for hand updates and gestures
        gm.OnHandUpdate.AddListener(OnHandUpdate);
        gm.OnGesture.AddListener(OnGesture);
    }

    private void OnHandUpdate(HandUpdateEvent evt)
    {
        var hand = GestureManager.Instance.GetHand(evt.hand_index);
        if (hand != null)
            _visualizer.UpdateHand(hand);
    }

    private void OnGesture(GestureEvent evt)
    {
        _currentGesture = evt.gesture;
        _currentConfidence = evt.confidence;
    }

    private void OnGUI()
    {
        if (!showGestureLabel || string.IsNullOrEmpty(_currentGesture))
            return;

        var style = new GUIStyle(GUI.skin.label)
        {
            fontSize = 32,
            alignment = TextAnchor.UpperCenter,
            normal = { textColor = Color.white }
        };

        GUI.Label(new Rect(0, 10, Screen.width, 50),
            $"{_currentGesture} ({_currentConfidence:P0})", style);
    }

    private void OnDestroy()
    {
        var gm = GestureManager.Instance;
        if (gm != null)
        {
            gm.OnHandUpdate.RemoveListener(OnHandUpdate);
            gm.OnGesture.RemoveListener(OnGesture);
        }
    }
}
